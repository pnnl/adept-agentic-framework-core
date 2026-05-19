import json
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from langchain_core.messages import ToolMessage
from .agent_state import AgentState


class AgentGraphBuilder:
    """Builds the custom LangGraph StateGraph for the ScientificWorkflowAgent.

    Some design discussions on workflow graph construction:

    In short, our custom StateGraph is more robust for our specific needs because it gives us complete control, whereas create_react_agent is a high-level utility that
    prioritizes ease of use over flexibility.

    Here’s a detailed breakdown of the trade-offs:

    create_react_agent (The Utility Function)

    This is a pre-packaged solution provided by LangGraph to quickly create a standard ReAct (Reasoning + Acting) agent.

    * Robustness in Simplicity:
       * High Reliability: It's built and maintained by the LangChain team and is optimized for the most common agent workflow. It's stable, well-tested, and less likely to
         have subtle bugs in its core looping logic.
       * Ease of Use: It requires very little boilerplate code. You provide a model and tools, and it handles the entire graph construction for you.

    * Where its "Robustness" Ends (The Limitations):
       * Inflexibility: It is a "black box." You cannot easily modify the internal workflow. We could not, for example, intercept the tool output to create our
         "split-stream" data flow.
       * Opacity: Because the internal logic is hidden, it can be harder to debug when things go wrong in non-standard ways. You don't have direct control over the nodes or
         the edges connecting them.

    Custom StateGraph (Our Current Approach)

    This approach involves manually defining every node (e.g., agent, action) and every edge (the logic that connects them).

    * Robustness in Control and Flexibility:
       * Maximum Control: This is its greatest strength. We have complete authority over the data flow. We were able to create a _custom_tool_node to intercept the tool's
         output, sanitize it for the LLM, and store the full version in our state. This is the kind of advanced, granular control that create_react_agent does not permit.
       * Transparency: The logic is explicit in our code. We can see exactly how the agent state is passed and modified at every step, which makes debugging complex
         interactions much easier.
       * Extensibility: It is far easier to add new, complex behaviors. If we wanted to add a human-in-the-loop approval step, a new conditional branch, or a
         "self-correction" loop, we could do so by adding new nodes and edges to our graph.

    * Where its "Robustness" Requires Care:
       * Increased Complexity: It is more verbose and requires a deeper understanding of LangGraph's state management.
       * Maintenance Overhead: We are now responsible for maintaining this workflow logic. If LangGraph introduces breaking changes to StateGraph, we might need to update
         our code, whereas create_react_agent would handle that internally.

    Comparison Table


    ┌──────────────┬──────────────────┬───────────────────┐
    │ Aspect       │ create_react_agent │ Custom StateGraph │
    ├──────────────┼──────────────────┼───────────────────┤
    │ Control      │ Low              │ High              │
    │ Flexibility  │ Low              │ High              │
    │ Simplicity   │ High             │ Low               │
    │ Transparency │ Low              │ High              │
    │ Maintenance  │ Low              │ Medium            │
    └──────────────┴──────────────────┴───────────────────┘

    Verdict

    The create_react_agent function is robust for standard agentic workflows. However, our requirement to manage the LLM's context by sanitizing tool outputs pushed us
    beyond what it could offer.

    Our custom StateGraph is more robust for our advanced use case precisely because it is flexible enough to accommodate the "split-stream" strategy. We traded the
    simplicity of the utility function for the power and control of a custom-built graph, which was necessary to solve the problem at hand.

    """

    def __init__(self, llm, tools: List[Any]):
        self.llm = llm
        self.tools = tools

    async def call_model(self, state: AgentState) -> dict:
        messages = state["messages"]
        ai_message = await self.llm.ainvoke(messages)
        return {"messages": [ai_message]}

    def should_continue(self, state: AgentState) -> str:
        last_message = state["messages"][-1]
        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return "end"
        return "continue"

    def _sanitize_tool_output(self, output: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize only 'plot' output; this is being very esoteric now.

        The sanitization logic is surgical and only activates under a very specific condition. It is handled by the _sanitize_tool_output method, which contains this check:

        1 if isinstance(output, dict) and "plots" in output and isinstance(output["plots"], list):
        2     # ... sanitization logic runs only inside this block ...

        This code acts as a guard:

        1. It first checks if the tool's output is a dictionary.
        2. It then checks if that dictionary explicitly contains a key named `"plots"`.

        Tool outputs from QueryUniProt or the web search tools return JSON that includes data like summaries, entries, or sequences, but they do not contain a "plots" key.

        Therefore, their output will fail the if condition, and the function will immediately return output without any modification. The full, original text data from those
        tools will be passed to the LLM, exactly as it was before.

        The sanitization is designed to be dormant unless it sees the specific signature of a plot-generating tool, ensuring it doesn't interfere with any other part of the
        workflow.

        """
        if (
            isinstance(output, dict)
            and "plots" in output
            and isinstance(output["plots"], list)
        ):
            sanitized_plots = []
            for plot in output["plots"]:
                if isinstance(plot, dict) and "content_base64" in plot:
                    sanitized_plot = plot.copy()
                    sanitized_plot["content_base64"] = (
                        f"<{sanitized_plot.get('format', 'image').upper()} data omitted, use plot_url>"
                    )
                    sanitized_plots.append(sanitized_plot)
            output["plots"] = sanitized_plots
        return output

    async def _custom_tool_node(self, state: AgentState) -> dict:
        tool_messages_for_llm = []
        full_tool_outputs_for_state = []
        last_message = state["messages"][-1]

        for tool_call in last_message.tool_calls:
            tool_to_call = next(
                (t for t in self.tools if t.name == tool_call["name"]), None
            )
            if not tool_to_call:
                raise ValueError(f"Tool '{tool_call['name']}' not found.")

            raw_output_str = await tool_to_call.ainvoke(tool_call["args"])
            raw_output_dict = json.loads(raw_output_str)
            full_tool_outputs_for_state.append(raw_output_dict)

            sanitized_output_dict = self._sanitize_tool_output(raw_output_dict)
            sanitized_output_str = json.dumps(sanitized_output_dict)

            tool_messages_for_llm.append(
                ToolMessage(content=sanitized_output_str, tool_call_id=tool_call["id"])
            )

        return {
            "messages": tool_messages_for_llm,
            "full_tool_outputs": full_tool_outputs_for_state,
        }

    def build(self) -> StateGraph:
        """Constructs and returns the StateGraph."""
        workflow = StateGraph(AgentState)
        workflow.add_node("agent", self.call_model)
        workflow.add_node("action", self._custom_tool_node)
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges(
            "agent", self.should_continue, {"continue": "action", "end": END}
        )
        workflow.add_edge("action", "agent")
        return workflow
