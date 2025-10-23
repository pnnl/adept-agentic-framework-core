# TODO: Remove/Replace Internal "Tanuki" References

This document lists all references to the internal "tanuki" GitLab/registry system that need to be updated for the public GitHub repository.

## Summary
- **Total matches found**: 98 instances across documentation and scripts
- **Action needed**: Remove SSH setup instructions and replace repository URLs with GitHub equivalents

---

## 1. Documentation Files - SSH Key Setup Instructions ✅ COMPLETED

These sections provided SSH setup instructions for the internal `tanuki-data.pnnl.gov` GitLab instance. **All have been removed** and replaced with GitHub HTTPS clone instructions.

### Main Documentation ✅
- **File**: `/docs/agentic-framework-tutorial.md`
  - **COMPLETED**: Removed entire SSH Key Setup section
  - **COMPLETED**: Updated clone command to:
    ```bash
    git clone https://github.com/pnnl/adept-agentic-framework-core.git
    cd adept-agentic-framework-core
    ```

### Tutorial Chapter Documentation ✅
All chapter tutorial files have been updated:

- ✅ `/docs/tutorial-branches/chapter-01-main/docs/agentic-framework-tutorial.md`
- ✅ `/docs/tutorial-branches/chapter-02-hpc-mcp-server-with-cot/docs/agentic-framework-tutorial.md`
- ✅ `/docs/tutorial-branches/chapter-03-llm-sandbox-and-multi-agent/docs/agentic-framework-tutorial.md`
- ✅ `/docs/tutorial-branches/chapter-04-kubernetes-deployment/docs/agentic-framework-tutorial.md`
- ✅ `/docs/tutorial-branches/chapter-05-openwebui-integration/docs/agentic-framework-tutorial.md`
- ✅ `/docs/tutorial-branches/chapter-06-advanced-multi-agent-orchestration/docs/agentic-framework-tutorial.md`

**All SSH setup sections removed and clone commands updated to GitHub HTTPS URL.**

---

## 2. HTML Demo Pages - Clone Commands ✅ COMPLETED

All HTML files have been updated with the correct GitHub clone command:

- ✅ `/docs/agentic-framework-page.html`
- ✅ `/docs/tutorial-branches/chapter-01-main/docs/agentic-framework-page.html`
- ✅ `/docs/tutorial-branches/chapter-02-hpc-mcp-server-with-cot/docs/agentic-framework-page.html`
- ✅ `/docs/tutorial-branches/chapter-03-llm-sandbox-and-multi-agent/docs/agentic-framework-page.html`
- ✅ `/docs/tutorial-branches/chapter-04-kubernetes-deployment/docs/agentic-framework-page.html`
- ✅ `/docs/tutorial-branches/chapter-05-openwebui-integration/docs/agentic-framework-page.html`
- ✅ `/docs/tutorial-branches/chapter-06-advanced-multi-agent-orchestration/docs/agentic-framework-page.html`

**All updated to**: `git clone https://github.com/pnnl/adept-agentic-framework-core.git`

---

## 3. Docker Registry Scripts ✅ COMPLETED

Scripts have been updated to use GitHub Container Registry (ghcr.io) with appropriate notices.

### Push Scripts ✅
- ✅ `/docs/tutorial-branches/chapter-04-kubernetes-deployment/scripts/docker-push_to_gitlab_tanuki.sh`
- ✅ `/docs/tutorial-branches/chapter-05-openwebui-integration/scripts/docker-push_to_gitlab_tanuki.sh`
- ✅ `/docs/tutorial-branches/chapter-06-advanced-multi-agent-orchestration/scripts/docker-push_to_gitlab_tanuki.sh`

**Updated**: Registry variable now points to `REGISTRY="ghcr.io/pnnl/adept-agentic-framework-core"`
**Added**: Notice about GitHub authentication requirements and documentation link

### Kubernetes Management Scripts ✅
- ✅ `/docs/tutorial-branches/chapter-04-kubernetes-deployment/scripts/helm-manage_emsl_k8s.sh`
- ✅ `/docs/tutorial-branches/chapter-05-openwebui-integration/scripts/helm-manage_emsl_k8s.sh`
- ✅ `/docs/tutorial-branches/chapter-06-advanced-multi-agent-orchestration/scripts/helm-manage_emsl_k8s.sh`

**Updated**: Registry server and image references to use ghcr.io
**Added**: Notice that script is configured for internal PNNL EMSL environment

---

## 4. Helm Chart Values ✅ COMPLETED

All Helm chart values files have been updated to use GitHub Container Registry (ghcr.io).

- ✅ `/docs/tutorial-branches/chapter-04-kubernetes-deployment/infra/helm/agentic-framework/values.yaml`
- ✅ `/docs/tutorial-branches/chapter-05-openwebui-integration/infra/helm/agentic-framework/values.yaml`
- ✅ `/docs/tutorial-branches/chapter-06-advanced-multi-agent-orchestration/infra/helm/agentic-framework/values.yaml`

**Updated repository references**:
```yaml
repository: ghcr.io/pnnl/adept-agentic-framework-core/mcp_server
repository: ghcr.io/pnnl/adept-agentic-framework-core/streamlit_app
repository: ghcr.io/pnnl/adept-agentic-framework-core/hpc_mcp_server
repository: ghcr.io/pnnl/adept-agentic-framework-core/sandbox_mcp_server
```

**Updated imagePullSecrets**:
- Secret name changed from `my-registry-secret` to `ghcr-secret`
- Documentation updated to show how to create secret for GitHub Container Registry
- Added note that images must be built and pushed to ghcr.io first

---

## Summary of Completed Work ✅

All recommended changes have been completed:

1. ✅ **HIGH PRIORITY**: Updated main tutorial documentation (`/docs/agentic-framework-tutorial.md`)
   - Removed SSH setup section
   - Replaced clone command with GitHub URL

2. ✅ **HIGH PRIORITY**: Updated all HTML demo pages with correct GitHub clone command
   - 7 HTML files updated across main docs and all tutorial chapters

3. ✅ **MEDIUM PRIORITY**: Updated tutorial chapter documentation (chapters 01-06)
   - All 6 chapter tutorial files updated with SSH removal and GitHub clone command

4. ✅ **MEDIUM PRIORITY**: Updated Helm chart values files
   - All 3 Helm values files now point to GitHub Container Registry (ghcr.io)
   - Updated documentation on creating image pull secrets

5. ✅ **LOW PRIORITY**: Updated internal scripts (docker-push, helm-manage)
   - All scripts updated with ghcr.io registry references
   - Added notices about internal PNNL use and GitHub authentication

---

## Next Steps for Repository Owner

### ⚠️ ACTION REQUIRED: Docker Image Publishing (Required for Kubernetes Deployment)

To make the Helm charts fully functional, you need to publish Docker images to GitHub Container Registry.

#### [ ] Task 1: Choose Image Publishing Strategy

**Option 1: Manual Build and Push**
```bash
# Authenticate with GitHub Container Registry
echo $GITHUB_PAT | docker login ghcr.io -u USERNAME --password-stdin

# Build and push each image
docker build -f Dockerfile.mcp_server -t ghcr.io/pnnl/adept-agentic-framework-core/mcp_server:latest .
docker push ghcr.io/pnnl/adept-agentic-framework-core/mcp_server:latest

# Repeat for other images: streamlit_app, hpc_mcp_server, sandbox_mcp_server
```

**Option 2: GitHub Actions (Recommended)**
- [ ] Create GitHub Actions workflow to automatically build and publish images
- [ ] Workflow should trigger on pushes to main branch and tags
- [ ] Build all Docker images (mcp_server, streamlit_app, hpc_mcp_server, sandbox_mcp_server)
- [ ] Push to ghcr.io with proper tagging (latest, version tags)
- [ ] Consider multi-platform builds if needed (amd64, arm64)

#### [ ] Task 2: Configure GitHub Repository Settings

- [ ] Enable GitHub Packages/Container Registry for the repository
- [ ] Create GitHub Personal Access Token (PAT) with `write:packages` permission
- [ ] Add PAT as repository secret (e.g., `GHCR_TOKEN`) if using GitHub Actions
- [ ] Configure package visibility (public recommended for open source)

#### [ ] Task 3: Test Image Publishing

- [ ] Build and push at least one image to verify ghcr.io access works
- [ ] Test pulling the image from ghcr.io
- [ ] Verify Helm chart can pull the image using ghcr-secret

#### [ ] Task 4: Update Documentation (if needed)

- [ ] Add section to main README about building/pulling Docker images
- [ ] Document how users can build images locally if they prefer
- [ ] Add instructions for creating ghcr-secret for Kubernetes deployments

#### [ ] Task 5: Review and Clean Up (Optional)

- [ ] Decide if internal PNNL scripts should remain in public repo
- [ ] Consider moving EMSL-specific scripts to separate internal documentation
- [ ] Verify all remaining "tanuki" references in script examples are acceptable

---

## Notes

- The internal "tanuki" system referred to PNNL's internal GitLab instance and Docker registry
- All references now point to GitHub repository and GitHub Container Registry (ghcr.io)
- Scripts that were internal PNNL-specific have been updated and documented accordingly
- Only 3 remaining "tanuki" references are in script filename examples (harmless)
