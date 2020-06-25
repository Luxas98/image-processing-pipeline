# Pre-requisities
1. create a static ip address
    a. either a regional (corresponds to L3/L4 Network LoadBalancer)
      `gcloud compute addresses create platform-ip`
    b. or global (corresponds to L7 HTTP(s) LoadBalancer / Ingress)
      `gcloud compute addresses create platform-ip --global`
2. create clusterrolebinding for cluster admin
    `kubectl create clusterrolebinding cluster-admin-binding \
        --clusterrole=cluster-admin \
        --user=$(gcloud config get-value core/account)`
3. for istio, get IP ranges
    `gcloud container clusters describe istio --zone=europe-west4-a \
         | grep -e clusterIpv4Cidr -e servicesIpv4Cidr`

# Istio + Cert Manager
## Reference: https://istio.io/docs/examples/advanced-gateways/ingress-certmgr/
1. install istio
    a. git clone repo
    b. generate manifests with helm template
        * enable https and certmanager incl. email (both crds and system)
        * enable sds
        * set ingressgateway service loadbalancer ip to static ip (regional)
    c. deploy and verify installed crds
        `kubectl get crds | grep 'istio.io\|certmanager.k8s.io' | wc -l`
    d. deploy istio
    e. patch ingressgateway to use SDS (Secret Discovery Service) for private key and cert
2. deploy app
  a. deploy openapi spec with static ip for cloud endpoints
  b. get and set config_id in deployment pod manifest
  c. apply deployment with kustomize
  d. deploy secrets for deployment pod (merge with kustomize deployment)
  e. deploy ingress with correct hostname and ingress class istio
3. enable istio-sidecar-injection 
4. deploy vritualservice, gateway and certificate into istio-system namespace
5. re-deploy app or kill/update the app pod

# NGINX Ingress + Istio + Cert Manager
1. install cert-manager and certificates (cluster-issuer and cert)
    * prod: dns
    * staging: http for cloud endpoints dns
    * install_cert_manager.sh script
    * deploy clusterissuer
2. install nginx controller with static ip
    a. git clone repo
    b. generate manifests with helm template
        * set correctly helm values: controller.service.loadBalancerIP
    c. deploy service namespace (api-gateway) with kubectl
    d. verify installed nginx controller and backend
3. deploy app
  a. deploy openapi spec with static ip for cloud endpoints
  b. get and set config_id in deployment pod manifest
  c. apply deployment with kustomize
  d. deploy secrets for deployment pod (merge with kustomize deployment)
  e. deploy ingress with correct hostname, ingress class nginx and tls spec
  f. deploy certificate

# IGINX Ingress + Istio + Cert Manager
## Reference: 
### * https://github.com/istio/istio/issues/3800
### * https://medium.com/ww-engineering/istio-part-ii-e219a2e771bb
1. install istio 
    a. download & prepare installation
    b. generate manifests with helm template
        * enable https and certmanager incl. email (both crds and system)
        * enable sds
        * set ingressgateway service type to NodePort (instead of LoadBalancer)
        * either with separate Ingress NGINX:
            `bash ./k8s/istio/generate_istio_w_separate_nginx.sh`
    c. deploy and verify installed crds
        `kubectl get crds | grep 'istio.io\|certmanager.k8s.io' | wc -l`
    d. deploy istio
        `bash ./k8s/istio/install_istio_w_separate_nginx.sh`
2. install nginx controller with static ip
    a. git clone repo
    b. generate manifests with helm template
        * set correctly helm values: controller.service.loadBalancerIP
    c. deploy into service namespace (ingressgateway) with kubectl
        `bash ./k8s/nginx-controller/install_nginx_controller.sh`
    d. verify installed nginx controller and backend
3. install cert-manager and certificates (cluster-issuer and cert)
    * prod: dns
    * staging: http for cloud endpoints dns
    * deploy with script
        `bash install_cert_manager.sh`
4. deploy app
  a. deploy openapi spec with static ip for cloud endpoints
  b. get and set config_id in deployment pod manifest
  c. apply deployment with kustomize
  d. deploy secrets for deployment pod (merge with kustomize deployment)
  e. deploy ingress with correct hostname, ingress class nginx and tls spec
    * NGINX Ingress points to istio's ingressgateway service
  f. deploy clusterissuer
  g. verify installed app with ingress running correctly
5. enable istio-sidecar-injection
    * verify installed app with ingress not working
6. deploy vritualservice, gateway and certificate (ingressgateway namespace)
7. re-deploy app or kill/update the app pod
8. re-deploy ingress with istio ingressgateway service backend
    * verify installed app with ingress running correctly

## Reference: https://istio.io/docs/examples/endpoints/
## TODOs:
* turn on mutual TLS
* turn on TLS certificate between NGINX Ingress and Istio ingressgateway
