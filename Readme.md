[1] *  Azure subscription 1  9d5850ea-385e-4eb6-be47-cbac9033c245  Default Directory

# stop the entire cluster
az aks stop --resource-group vaccine-cold-chain-rg --name vaccine-aks-cluster

# Scale to zero 
az aks nodepool scale \
  --resource-group vaccine-cold-chain-rg \
  --cluster-name vaccine-aks-cluster \
  --name workload \
  --node-count 0

# more elegant scale to zero
az aks nodepool scale \
  --resource-group vaccine-cold-chain-rg \
  --cluster-name vaccine-aks-cluster \
  --name workload \
  --node-count 0

# check pool
az aks nodepool list --resource-group vaccine-cold-chain-rg --cluster-name vaccine-aks-cluster




