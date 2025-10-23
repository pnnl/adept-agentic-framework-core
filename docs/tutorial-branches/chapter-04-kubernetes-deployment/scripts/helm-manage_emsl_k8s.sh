#!/bin/bash

# NOTE: This script is configured for internal PNNL EMSL Kubernetes environment.
# Public users should refer to the main Helm deployment documentation.
# Registry references have been updated to ghcr.io in values.yaml files.


# For safety, ensure this script is run with bash with -e option
# We'll handle errors more gracefully within the script for better user experience.
# set -euo pipefail

# For sanity, ensure that this script is run in the correct directory, e.g., the root of the agentic_framework project
if [ ! -f "./infra/helm/agentic-framework/values.yaml" ]; then
    echo "ERROR: This script must be run from the root of the agentic_framework project (where ./infra/helm/agentic-framework/values.yaml is found)."
    exit 1
fi

# --- Configuration Variables ---
# !!! IMPORTANT: Adjust these paths and names to match your environment !!!
K8S_CLIENT_BUNDLE_PATH="${PWD}/scripts/deps/emsl-helm/macos/"
KUBECTL_BIN="${K8S_CLIENT_BUNDLE_PATH}/kubectl"
HELM_BIN="${K8S_CLIENT_BUNDLE_PATH}/helm"
# We now explicitly require 'docker' for image checks
DOCKER_BIN="/usr/local/bin/docker" # You might need to adjust this path

KUBECONFIG_PATH="${K8S_CLIENT_BUNDLE_PATH}/emslrzr.config:${K8S_CLIENT_BUNDLE_PATH}/emslrzr.config.cluster"
HELM_CHART_PATH="./infra/helm/agentic-framework/"
VALUES_FILE="./infra/helm/agentic-framework/values.yaml"
RELEASE_NAME="my-agentic-release"
NAMESPACE="class"
REGISTRY_SERVER="ghcr.io"
LOG_FILE="./helm-manage.log"
REGISTRY_SECRET_NAME="ghcr-secret" # Must match 'imagePullSecrets.name' in values.yaml

# --- .env Secret Configuration ---
ENV_FILE="./.env" # Path to your .env file
APP_SECRET_NAME="my-app-env-secret" # Name of the Kubernetes secret to be created from .env

# --- PVC Wait Configuration ---
PVC_WAIT_TIMEOUT=300 # seconds (5 minutes)
PVC_WAIT_INTERVAL=10 # seconds

# --- REQUIRED IMAGES IN REGISTRY ---
# List all the images your Helm chart expects to pull from the registry
REQUIRED_IMAGES=(
    "ghcr.io/pnnl/adept-agentic-framework-core/agentic_framework-hpc_mcp_server:latest"
    "ghcr.io/pnnl/adept-agentic-framework-core/agentic_framework-mcp_server:latest"
    "ghcr.io/pnnl/adept-agentic-framework-core/agentic_framework-streamlit_app:latest"
    "ghcr.io/pnnl/adept-agentic-framework-core/agentic_framework-sandbox_mcp_server:latest"
)

# --- Helper Functions ---

# Function to log messages with a timestamp
log_message() {
    local type="$1" # INFO, WARN, ERROR
    local message="$2"
    echo -e "$(date '+%Y-%m-%d %H:%M:%S') [$type] $message" | tee -a "$LOG_FILE"
}

# Function to execute kubectl with correct KUBECONFIG and PATH
kctl() {
    # Ensure all variables are quoted to handle spaces or special characters
    KUBECONFIG="${KUBECONFIG_PATH}" PATH="${K8S_CLIENT_BUNDLE_PATH}:$PATH" "${KUBECTL_BIN}" "$@"
}

# Function to execute helm with correct KUBECONFIG and PATH
hlm() {
    # Ensure all variables are quoted to handle spaces or special characters
    KUBECONFIG="${KUBECONFIG_PATH}" PATH="${K8S_CLIENT_BUNDLE_PATH}:$PATH" "${HELM_BIN}" "$@"
}

# Prints the script usage instructions
print_usage() {
    echo "Usage: $0 {spin-up|upgrade|restart|tear-down|status}"
    echo "  spin-up: Creates/updates secrets and installs/upgrades Helm chart."
    echo "  upgrade: Upgrades an existing Helm release with new images or configuration."
    echo "  restart [component]: Gracefully restarts deployments. If a component (e.g., streamlit-app) is specified, only that deployment is restarted. Otherwise, all deployments in the release are restarted. This is useful to force a pull of an image with a 'latest' tag."
    echo "  tear-down: Deletes Helm release and all its resources, including custom secrets."
    echo "  status: Shows status of PVCs, Pods, Pod Events, and Secrets."
}

# Checks for the existence of necessary binaries and files.
# Does not exit immediately on error, but collects them.
check_prerequisites() {
    log_message "INFO" "--- Checking prerequisites ---"
    local errors=0

    # Check binaries
    if [ ! -f "${KUBECTL_BIN}" ]; then
        log_message "ERROR" "kubectl binary not found at ${KUBECTL_BIN}"
        errors=1
    fi
    if [ ! -f "${HELM_BIN}" ]; then
        log_message "ERROR" "helm binary not found at ${HELM_BIN}"
        errors=1
    fi
    # Check for docker binary
    if ! command -v "${DOCKER_BIN}" &> /dev/null; then
        log_message "ERROR" "docker binary not found or not executable at ${DOCKER_BIN}. Please ensure Docker Desktop is running or Docker CLI is installed and in your PATH."
        errors=1
    fi
    # No longer need curl for image checks, but you might need it for other things.
    # if ! command -v curl &> /dev/null; then
    #     log_message "ERROR" "curl command not found. Please install curl."
    #     errors=1
    # fi


    # Check Helm chart and values file paths
    if [ ! -d "${HELM_CHART_PATH}" ]; then
        log_message "ERROR" "Helm chart path not found at ${HELM_CHART_PATH}"
        errors=1
    fi
    if [ ! -f "${VALUES_FILE}" ]; then
        log_message "ERROR" "values.yaml not found at ${VALUES_FILE}"
        errors=1
    fi

    # Check for .env file (warning only, as it might be optional)
    if [ ! -f "${ENV_FILE}" ]; then
        log_message "WARN" ".env file not found at ${ENV_FILE}. Application secrets may be incomplete if your chart relies on it."
    fi

    if [ "$errors" -ne 0 ]; then
        log_message "ERROR" "One or more critical prerequisites failed. Please resolve the errors."
        exit 1 # Exit if there were critical errors that prevent any operation
    fi
    log_message "INFO" "Prerequisites checked successfully."
}

# Creates or recreates the Docker registry secret from user input.
create_docker_registry_secret() {
    log_message "INFO" "--- Creating/Ensuring Docker Registry Secret ---"

    local DOCKER_USERNAME DOCKER_PASSWORD DOCKER_EMAIL

    # Prompt for credentials within the function where they are needed
    read -p "Enter Docker Registry Username for ${REGISTRY_SERVER}: " DOCKER_USERNAME
    read -s -p "Enter Docker Registry Password for ${REGISTRY_SERVER}: " DOCKER_PASSWORD
    echo # New line after password input
    read -p "Enter Docker Registry Email (optional): " DOCKER_EMAIL

    # Basic validation for required credentials
    if [ -z "${DOCKER_USERNAME}" ] || [ -z "${DOCKER_PASSWORD}" ]; then
        log_message "ERROR" "Docker Registry Username and Password are required to create the secret and perform registry checks."
        return 1 # Return error, don't exit script entirely
    fi

    # Log in Docker CLI to the registry (important for check_registry_images)
    log_message "INFO" "--- Logging in Docker CLI to ${REGISTRY_SERVER} ---"
    # Use --password-stdin to avoid password on command line in history
    if ! "${DOCKER_BIN}" login "${REGISTRY_SERVER}" -u "${DOCKER_USERNAME}" --password-stdin <<< "${DOCKER_PASSWORD}" >/dev/null 2>&1; then
        log_message "ERROR" "Docker CLI login failed to ${REGISTRY_SERVER}. Please check credentials."
        return 1
    fi
    log_message "INFO" "Docker CLI successfully logged into ${REGISTRY_SERVER}."


    # Check if secret already exists and delete if so
    if kctl get secret "${REGISTRY_SECRET_NAME}" -n "${NAMESPACE}" &> /dev/null; then
        log_message "INFO" "Secret '${REGISTRY_SECRET_NAME}' already exists. Attempting to delete and recreate."
        kctl delete secret "${REGISTRY_SECRET_NAME}" -n "${NAMESPACE}" || { log_message "ERROR" "Failed to delete existing secret. Exiting."; exit 1; }
        sleep 2 # Give Kubernetes a moment for deletion to propagate
    fi

    # Create the secret
    kctl create secret docker-registry "${REGISTRY_SECRET_NAME}" \
        --docker-server="${REGISTRY_SERVER}" \
        --docker-username="${DOCKER_USERNAME}" \
        --docker-password="${DOCKER_PASSWORD}" \
        --docker-email="${DOCKER_EMAIL}" \
        --namespace "${NAMESPACE}" || { log_message "ERROR" "Failed to create docker-registry secret. Exiting."; exit 1; }
    log_message "INFO" "Docker Registry Secret '${REGISTRY_SECRET_NAME}' created successfully in namespace '${NAMESPACE}'."
    return 0
}

# Creates or recreates a generic Kubernetes secret from a .env file.
create_app_env_secret() {
    log_message "INFO" "--- Creating/Ensuring Application Environment Secret from ${ENV_FILE} ---"

    if [ ! -f "${ENV_FILE}" ]; then
        log_message "WARN" "Skipping .env secret creation: ${ENV_FILE} not found. Please create it if your application needs it."
        return 0 # Not a critical error, just skip
    fi

    # Check if secret already exists and delete if so
    if kctl get secret "${APP_SECRET_NAME}" -n "${NAMESPACE}" &> /dev/null; then
        log_message "INFO" "Secret '${APP_SECRET_NAME}' already exists. Attempting to delete and recreate."
        kctl delete secret "${APP_SECRET_NAME}" -n "${NAMESPACE}" || { log_message "ERROR" "Failed to delete existing app secret. Exiting."; exit 1; }
        sleep 2 # Give Kubernetes a moment
    fi

    # Create the secret from the .env file
    kctl create secret generic "${APP_SECRET_NAME}" \
        --from-env-file="${ENV_FILE}" \
        --namespace "${NAMESPACE}" || { log_message "ERROR" "Failed to create application environment secret from ${ENV_FILE}. Exiting."; exit 1; }
    log_message "INFO" "Application Environment Secret '${APP_SECRET_NAME}' created successfully in namespace '${NAMESPACE}'."
    return 0
}

# Waits for all PVCs associated with the release to be Bound.
wait_for_pvc_bound() {
    log_message "INFO" "--- Waiting for PVCs to be Bound ---"
    local start_time=$(date +%s)
    local elapsed_time=0
    local all_pvcs_bound=false

    while [ "${elapsed_time}" -lt "${PVC_WAIT_TIMEOUT}" ]; do
        # Get count of Pending PVCs for this release
        local pending_pvcs=$(kctl get pvc -n "${NAMESPACE}" -l app.kubernetes.io/instance="${RELEASE_NAME}" \
                                 --field-selector status.phase=Pending -o name 2>/dev/null | wc -l)
        
        if [ "${pending_pvcs}" -eq 0 ]; then
            all_pvcs_bound=true
            break
        fi

        log_message "INFO" "Still waiting for ${pending_pvcs} PVC(s) to become Bound (waited ${elapsed_time}s/${PVC_WAIT_TIMEOUT}s)..."
        sleep "${PVC_WAIT_INTERVAL}"
        elapsed_time=$(( $(date +%s) - start_time ))
    done

    if [ "${all_pvcs_bound}" = true ]; then
        log_message "INFO" "All PVCs for release '${RELEASE_NAME}' are Bound."
        return 0
    else
        log_message "ERROR" "PVCs for release '${RELEASE_NAME}' did not become Bound within ${PVC_WAIT_TIMEOUT} seconds."
        kctl get pvc -n "${NAMESPACE}" -l app.kubernetes.io/instance="${RELEASE_NAME}" # Show final state
        kctl describe pvc -n "${NAMESPACE}" -l app.kubernetes.io/instance="${RELEASE_NAME}" # Show events for troubleshooting
        return 1
    fi
}

# --- UPDATED FUNCTION: Checks if required images exist in the container registry using 'docker manifest inspect' ---
check_registry_images() {
    log_message "INFO" "--- Verifying Required Images in Registry (via 'docker manifest inspect') ---"
    local missing_images=()
    
    for image in "${REQUIRED_IMAGES[@]}"; do
        log_message "INFO" "Checking image: ${image}..."
        # Try to inspect the image manifest.
        # This will query the registry for the manifest and return 0 if found.
        # It does NOT pull the full image layers.
        # It leverages the 'docker login' credentials stored in ~/.docker/config.json.
        if ! "${DOCKER_BIN}" manifest inspect "${image}" >/dev/null 2>&1; then
            log_message "WARN" "Image ${image} not found or inaccessible in registry."
            missing_images+=("${image}")
        else
            log_message "INFO" "Image ${image} found."
        fi
    done

    if [ ${#missing_images[@]} -ne 0 ]; then
        log_message "ERROR" "The following required images were NOT found or accessible in the registry:"
        for missing in "${missing_images[@]}"; do
            log_message "ERROR" "  - ${missing}"
        done
        log_message "ERROR" "Please ensure these images are pushed to ${REGISTRY_SERVER} and that your Docker CLI has permission to access them."
        return 1 # Indicate failure
    else
        log_message "INFO" "All required images found and accessible in the registry."
        return 0 # Indicate success
    fi
}

# Restarts deployments to force a refresh (e.g., to pull a new 'latest' image).
# Can restart all deployments in the release or a specific one if a component name is provided.
restart() {
    log_message "INFO" "--- Restarting deployments for release ${RELEASE_NAME} in namespace ${NAMESPACE} ---"
    check_prerequisites

    local component_to_restart="$1"
    
    if [ -n "${component_to_restart}" ]; then
        # User specified a component to restart
        # Validate component name
        local valid_components=("mcp-server" "streamlit-app" "hpc-mcp-server" "sandbox-mcp-server")
        if [[ ! " ${valid_components[*]} " =~ " ${component_to_restart} " ]]; then
            log_message "ERROR" "Invalid component name '${component_to_restart}'."
            log_message "INFO" "Valid components are: ${valid_components[*]}"
            exit 1
        fi

        # Construct the full deployment name based on Helm's naming convention
        # Assumes default fullname template: {{ .Release.Name }}-{{ .Chart.Name }}
        local chart_name
        chart_name=$(basename "${HELM_CHART_PATH}")
        local full_name="${RELEASE_NAME}-${chart_name}"
        local target_deployment="${full_name}-${component_to_restart}"

        log_message "INFO" "Targeting specific deployment for restart: ${target_deployment}"
        kctl rollout restart deployment "${target_deployment}" -n "${NAMESPACE}" \
            || { log_message "ERROR" "Failed to restart deployment '${target_deployment}'. Does it exist?"; exit 1; }
        log_message "INFO" "Deployment '${target_deployment}' is being restarted."
    else
        # No component specified, restart all deployments for the release using the label selector
        log_message "INFO" "Restarting all deployments for release '${RELEASE_NAME}'..."
        kctl rollout restart deployment -n "${NAMESPACE}" -l app.kubernetes.io/instance="${RELEASE_NAME}" \
            || { log_message "ERROR" "Failed to restart deployments for release '${RELEASE_NAME}'."; exit 1; }
        log_message "INFO" "All deployments for release '${RELEASE_NAME}' are being restarted."
    fi

    log_message "INFO" "Rollout restart initiated. Use the 'status' command to monitor the new pods."
}

# Logs into the Docker CLI, prompting for credentials only if necessary.
login_docker_cli() {
    log_message "INFO" "--- Checking Docker CLI login status for ${REGISTRY_SERVER} ---"
    # Attempt to inspect a manifest. If it succeeds, we are logged in.
    if "${DOCKER_BIN}" manifest inspect "${REQUIRED_IMAGES[0]}" >/dev/null 2>&1; then
        log_message "INFO" "Docker CLI is already logged in and has access to the registry."
        return 0
    fi

    log_message "INFO" "Docker CLI login required or token has expired."
    local DOCKER_USERNAME DOCKER_PASSWORD
    read -p "Enter Docker Registry Username for ${REGISTRY_SERVER}: " DOCKER_USERNAME
    read -s -p "Enter Docker Registry Password for ${REGISTRY_SERVER}: " DOCKER_PASSWORD
    echo # New line

    if [ -z "${DOCKER_USERNAME}" ] || [ -z "${DOCKER_PASSWORD}" ]; then
        log_message "ERROR" "Docker Registry Username and Password are required."
        return 1
    fi

    if ! "${DOCKER_BIN}" login "${REGISTRY_SERVER}" -u "${DOCKER_USERNAME}" --password-stdin <<< "${DOCKER_PASSWORD}" >/dev/null 2>&1; then
        log_message "ERROR" "Docker CLI login failed to ${REGISTRY_SERVER}. Please check credentials."
        return 1
    fi
    log_message "INFO" "Docker CLI successfully logged into ${REGISTRY_SERVER}."
    return 0
}

# Upgrades an existing Helm release.
upgrade() {
    log_message "INFO" "--- Upgrading existing release ${RELEASE_NAME} in namespace ${NAMESPACE} ---"
    check_prerequisites

    # 1. Check if release exists
    if ! hlm status "${RELEASE_NAME}" -n "${NAMESPACE}" &> /dev/null; then
        log_message "ERROR" "Helm release '${RELEASE_NAME}' not found in namespace '${NAMESPACE}'."
        log_message "INFO" "Please use the 'spin-up' command for the initial installation."
        exit 1
    fi

    # 2. Login to docker and check images
    login_docker_cli || { log_message "ERROR" "Docker login failed. Aborting upgrade."; exit 1; }
    check_registry_images || { log_message "ERROR" "Required images not found in registry. Aborting upgrade."; exit 1; }

    # 3. Run helm upgrade
    log_message "INFO" "--- Upgrading Helm Chart ---"
    hlm upgrade "${RELEASE_NAME}" "${HELM_CHART_PATH}" \
        --namespace "${NAMESPACE}" \
        -f "${VALUES_FILE}" --atomic --timeout 5m \
        || { log_message "ERROR" "Helm upgrade failed. Exiting."; exit 1; }

    # 4. Restart deployments to ensure they pick up config changes if any
    log_message "INFO" "--- Triggering rollout restart of deployments to apply changes ---"
    kctl rollout restart deployment -n "${NAMESPACE}" -l app.kubernetes.io/instance="${RELEASE_NAME}" \
        || { log_message "WARN" "Failed to trigger rollout restart. Pods may not update immediately. You can monitor with 'status' or manually delete pods to force a refresh."; }

    log_message "INFO" "Helm release '${RELEASE_NAME}' upgraded successfully."
    log_message "INFO" "Use 'status' command to monitor the new pods."
}


# Spins up (installs/upgrades) the Helm chart and necessary secrets.
spin_up() {
    log_message "INFO" "--- Spinning up resources for ${RELEASE_NAME} in namespace ${NAMESPACE} ---"
    
    # Ensure critical prerequisites are met before proceeding with actual deployment
    check_prerequisites # Re-checking here for robustness

    # Create necessary secrets before Helm deployment
    # This step also performs 'docker login' which is essential for check_registry_images
    create_docker_registry_secret || { log_message "ERROR" "Failed to create Docker registry secret. Aborting spin-up."; exit 1; }
    create_app_env_secret # This function handles its own errors/warnings

    # --- Verify Images in Registry ---
    # This step is crucial and must come AFTER docker login via create_docker_registry_secret
    check_registry_images || { log_message "ERROR" "Required images not found in registry. Aborting spin-up."; exit 1; }

    # --- Deploy Helm Chart to create PVCs and other resources ---
    log_message "INFO" "--- Installing/Upgrading Helm Chart to create initial resources (including PVCs) ---"
    
    # Note: let's no pass the --create-namespace flag here, as we assume the namespace already exists, according
    # to our privileges per the EMSL admin team.
    hlm upgrade --install "${RELEASE_NAME}" "${HELM_CHART_PATH}" \
        --namespace "${NAMESPACE}" \
        -f "${VALUES_FILE}" --atomic --timeout 5m \
        || { log_message "ERROR" "Helm installation/upgrade failed for initial resource creation. Exiting."; exit 1; }

    # --- Wait for PVCs to be Bound ---
    wait_for_pvc_bound || { log_message "ERROR" "PVCs did not become bound. Aborting spin-up."; exit 1; }

    # --- Re-run Helm Upgrade (or just ensure deployments are processed) ---
    log_message "INFO" "--- Ensuring deployments are updated after PVCs are bound ---"
    kctl rollout restart deployment -n "${NAMESPACE}" -l app.kubernetes.io/instance="${RELEASE_NAME}" \
        || { log_message "ERROR" "Failed to trigger rollout restart. Pods might remain pending. Exiting."; exit 1; }


    log_message "INFO" "Resources are being spun up. Use 'status' command to monitor."
}

# Tears down (uninstalls) the Helm chart and deletes custom secrets.
tear_down() {
    log_message "INFO" "--- Tearing down resources for ${RELEASE_NAME} in namespace ${NAMESPACE} ---"
    check_prerequisites # Re-checking here for robustness

    read -p "Are you sure you want to uninstall Helm release '${RELEASE_NAME}' in namespace '${NAMESPACE}'? This will delete all associated resources including PVCs and potentially data. (yes/no): " confirm
    if [[ "$confirm" != "yes" ]]; then
        log_message "INFO" "Aborted."
        return 0
    fi

    # Make helm uninstall more resilient with a timeout and continue on error
    if ! hlm uninstall "${RELEASE_NAME}" --namespace "${NAMESPACE}" --timeout 5m --wait=false; then
        log_message "WARN" "Helm uninstallation of '${RELEASE_NAME}' might have encountered issues or timed out. Proceeding with secret cleanup."
        # If you want more debug info on Helm failure here, you could add:
        # hlm get manifest "${RELEASE_NAME}" --namespace "${NAMESPACE}" || true
    else
        log_message "INFO" "Helm release '${RELEASE_NAME}' uninstallation completed (or started) successfully."
    fi
    
    log_message "INFO" "--- Deleting Application Environment Secret ---"
    # Only delete if it exists to avoid errors
    if kctl get secret "${APP_SECRET_NAME}" -n "${NAMESPACE}" &> /dev/null; then
        kctl delete secret "${APP_SECRET_NAME}" -n "${NAMESPACE}" || log_message "WARN" "Failed to delete app secret. Manual cleanup may be required."
    else
        log_message "INFO" "Application environment secret '${APP_SECRET_NAME}' not found. Skipping deletion."
    fi

    log_message "INFO" "--- Deleting Docker Registry Secret ---"
    # Only delete if it exists to avoid errors
    if kctl get secret "${REGISTRY_SECRET_NAME}" -n "${NAMESPACE}" &> /dev/null; then
        kctl delete secret "${REGISTRY_SECRET_NAME}" -n "${NAMESPACE}" || log_message "WARN" "Failed to delete docker registry secret. Manual cleanup may be required."
    else
        log_message "INFO" "Docker registry secret '${REGISTRY_SECRET_NAME}' not found. Skipping deletion."
    fi

    log_message "INFO" "Tear-down process completed." # Final confirmation
}

# Shows the current status of PVCs, Pods, Pod Events, and Secrets.
status_check() {
    log_message "INFO" "--- Status Check for ${RELEASE_NAME} in namespace ${NAMESPACE} ---"
    check_prerequisites # Re-checking here for robustness

    log_message "INFO" "--- Persistent Volume Claims (PVCs) Status ---"
    kctl get pvc -n "${NAMESPACE}" -l app.kubernetes.io/instance="${RELEASE_NAME}"

    log_message "INFO" "--- Pods Status ---"
    kctl get pods -n "${NAMESPACE}" -l app.kubernetes.io/instance="${RELEASE_NAME}"

    log_message "INFO" "--- Pod Events (Last 10 events per pod) ---"
    POD_NAMES=$(kctl get pods -n "${NAMESPACE}" -l app.kubernetes.io/instance="${RELEASE_NAME}" -o jsonpath='{.items[*].metadata.name}')
    if [ -z "$POD_NAMES" ]; then
        log_message "INFO" "No pods found for release '${RELEASE_NAME}' in namespace '${NAMESPACE}'."
    else
        for POD_NAME in $POD_NAMES; do
            log_message "INFO" "--- Events for Pod: ${POD_NAME} ---"
            # Limit to last 10 events for brevity
            kctl describe pod "${POD_NAME}" -n "${NAMESPACE}" | awk '/^Events:/,/^$/' | head -n 11
        done
    fi

    log_message "INFO" "--- Secrets in Namespace ${NAMESPACE} ---"
    # List Helm-managed secrets (often labeled by Helm)
    log_message "INFO" "Helm-managed secrets:"
    kctl get secrets -n "${NAMESPACE}" -l app.kubernetes.io/instance="${RELEASE_NAME}" 2>/dev/null || log_message "INFO" "No Helm-managed secrets found for this release."
    
    # Explicitly check for the custom secrets created by the script
    log_message "INFO" "Script-managed secrets:"
    kctl get secrets "${REGISTRY_SECRET_NAME}" "${APP_SECRET_NAME}" -n "${NAMESPACE}" 2>/dev/null || log_message "INFO" "Custom secrets '${REGISTRY_SECRET_NAME}' or '${APP_SECRET_NAME}' not found."
}

# --- Main Script Logic ---

# Check if an argument is provided. If not, print usage and exit.
if [ -z "$1" ]; then
    print_usage
    exit 1
fi

# Execute the appropriate function based on the first argument.
# We call check_prerequisites inside each main function as well for robustness
# if someone bypasses the initial argument check (e.g., sourcing the script).
case "$1" in
    spin-up)
        spin_up
        ;;
    upgrade)
        upgrade
        ;;
    restart)
        restart "$2" # Pass the second argument (component name) to the function
        ;;
    tear-down)
        tear_down
        ;;
    status)
        status_check
        ;;
    help|--help|-h)
        print_usage # Print usage if help is requested
        ;;
    *)
        log_message "ERROR" "Invalid command. Please use 'spin-up', 'upgrade', 'restart', 'tear-down', or 'status'."
        print_usage # Print usage on invalid command
        exit 1
        ;;
esac