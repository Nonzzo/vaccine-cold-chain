# Vaccine Cold Chain — Platform

High-quality proof-of-concept platform for secure telemetry, ingestion, storage, and processing of vaccine-cold-chain sensor data. Demonstrates an end-to-end cloud-native architecture using Azure, Kubernetes, Kafka (Strimzi KRaft), PostgreSQL, observability and infrastructure-as-code.

Tech stack
- Cloud: Azure (AKS, Managed Identities, Storage, PostgreSQL Flexible Server)
- Infra: Terraform
- Kubernetes: AKS, manifests under k8s/
- Streaming: Apache Kafka via Strimzi (KRaft mode + KafkaNodePool)
- DB: PostgreSQL (container example + managed option in Terraform)
- Observability: Prometheus, Grafana
- CI/CD: GitHub Actions (workflows/deploy.yaml)
- Container runtime: Docker (producer/consumer services in src/)
- Languages: Python (simple producer/consumer examples)



Repository layout
- terraform/ — Terraform infra (AKS, storage, optionally PostgreSQL flexible server)
  - envs/dev.tfvars — environment variables
  - main.tf, outputs.tf, variables.tf
- k8s/ — Kubernetes manifests
  - kafka/ — Strimzi Kafka + KafkaNodePool manifests
  - database/ — PostgreSQL PVC + deployment example
  - monitoring/ — Prometheus/Grafana manifests
  - apps/ — app deployment templates
- src/
  - producer/ — sample producer (Dockerfile + Python)
  - consumer/ — sample consumer (Dockerfile + Python)
- .github/workflows/deploy.yaml — CI/CD pipeline
- .gitignore — secrets & state ignored

Quick start (developer)
1. Prereqs (macOS)
   - Azure CLI: az
   - Terraform >= 1.4
   - kubectl
   - docker
   - jq (optional)
2. Prepare env
   - cd terraform
   - copy envs/dev.tfvars.example → envs/dev.tfvars and set values (location, resource group, identity id if using UAI)

3. Obtain kubeconfig
   - Preferred: let Terraform write kubeconfig (recommended change: add local_file resource)
   - Quick merge from state (sensitive data): 
     - terraform state pull | jq -r '.resources[] | select(.type=="azurerm_kubernetes_cluster" and .name=="aks") | .instances[0].attributes.kube_config_raw' > /tmp/aks_kube.yaml
     - Backup and merge:
       - cp $HOME/.kube/config $HOME/.kube/config.bak
       - KUBECONFIG=$HOME/.kube/config:/tmp/aks_kube.yaml kubectl config view --flatten > /tmp/merged && mv /tmp/merged $HOME/.kube/config
       - kubectl config use-context aks-vaccine-cluster
4. Deploy platform components
   - kubectl apply -f k8s/kafka           # Strimzi operator + Kafka & nodepool manifests
   - kubectl apply -f k8s/database       # PostgreSQL example (see notes)
   - kubectl apply -f k8s/monitoring
   - kubectl apply -f k8s/apps           # producer/consumer deployments if templated
5. Verify
   - kubectl -n kafka get pods
   - kubectl -n kafka get pvc,pv
   - kubectl -n kafka logs deployment/strimzi-cluster-operator

Troubleshooting (short reference)
- AKS identity error (Location mismatch / AAD SP exists): prefer user-assigned managed identity (UAI) for AKS; grant UAI Contributor on RG. If deleting AAD SP, you need Azure AD admin privileges.
- vCPU quota error: Free Trial subscriptions cannot request quota increases. Options: reduce node counts/VM sizes, choose another region, or upgrade subscription.
- Postgres initdb fails (lost+found): set PGDATA to a subdirectory under the PVC mount (e.g. `/var/lib/postgresql/data/pgdata`) so initdb sees an empty directory.
- PVC stuck/Released: if reclaimPolicy=Retain, delete PV and the underlying Azure Disk manually after PVC deletion.
- Strimzi KRaft + NodePools:
  - Use `apiVersion: kafka.strimzi.io/v1` and `strimzi.io/node-pools: "enabled"`.
  - Define broker storage & replica counts in KafkaNodePool resources (not inside spec.kafka).
  - Ensure Strimzi operator version supports KRaft + node pools.

Security & secrets
- No secrets checked into the repo. .gitignore ignores tfvars, kubeconfig, logs.
- Use Azure Key Vault or Kubernetes Secrets for credentials 

CI/CD
- GitHub Actions in .github/workflows/deploy.yaml demonstrate a deploy pipeline (build images, push to registry, apply manifests).
- Use a secure image registry and GitHub Secrets for credentials.



License
- MIT (add LICENSE file as needed)


