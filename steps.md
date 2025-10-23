## Root CA
vault secrets enable pki

vault secrets tune -max-lease-ttl=87600h pki

vault write -field=certificate pki/root/generate/internal \
     common_name="example.com" \
     issuer_name="root-2023" \
     ttl=87600h > root_2023_ca.crt

vault list pki/issuers/

vault read pki/issuer/$(vault list -format=json pki/issuers/ | jq -r '.[]') \
 | tail -n 6

vault write pki/roles/2023-servers allow_any_name=true

vault write pki/config/urls \
    issuing_certificates="$VAULT_ADDR/v1/pki/ca" \
    crl_distribution_points="$VAULT_ADDR/v1/pki/crl"


## Intermediate CA

vault secrets enable -path=pki_int pki

vault secrets tune -max-lease-ttl=43800h pki_int

vault write -format=json pki_int/intermediate/generate/internal \
     common_name="example.com Intermediate Authority" \
     issuer_name="example-dot-com-intermediate" \
     | jq -r '.data.csr' > pki_intermediate.csr

vault write -format=json pki/root/sign-intermediate \
     issuer_ref="root-2023" \
     csr=@pki_intermediate.csr \
     format=pem_bundle ttl="43800h" \
     | jq -r '.data.certificate' > intermediate.cert.pem

vault write pki_int/intermediate/set-signed certificate=@intermediate.cert.pem

vault write pki_int/roles/example-dot-com \
     issuer_ref="$(vault read -field=default pki_int/config/issuers)" \
     allowed_domains="example.com" \
     allow_subdomains=true \
     max_ttl="720h"


## Request certificates
vault write pki_int/issue/example-dot-com common_name="api.example.com" ttl="720h"

vault write pki_int/revoke serial_number="61:f6:7a:dd:71:d2:1c:c0:40:2e:58:cd:ef:d9:cb:6e:15:38:10:08"


## List certs
v list pki/certs
v list pki_int/certs

v read -format=json pki_int/cert/61:f6:7a:dd:71:d2:1c:c0:40:2e:58:cd:ef:d9:cb:6e:15:38:10:08  | jq '.data.certificate' -r | openssl x509 -text -noout

v list pki_int/issuers
v read -format=json pki_int/issuer/8eedc725-2f47-941c-1b28-e200211b4e0e  | jq '.data.certificate' -r | openssl x509 -text -noout

## List issuers
curl \
  -H "X-Vault-Token: $VAULT_TOKEN" \
  -H "X-Vault-Namespace: admin" \
  -H "X-Vault-Request: true" \
  -X LIST \
  $VAULT_ADDR/v1/pki_int/issuers | jq .

## List keys/serial-no of all certs 
curl -s\
  -H "X-Vault-Token: $VAULT_TOKEN" \
  -H "X-Vault-Namespace: admin" \
  -H "X-Vault-Request: true" \
  -X LIST \
  $VAULT_ADDR/v1/pki_int/certs | jq .

## Read cert by key
curl -s\
  -H "X-Vault-Token: $VAULT_TOKEN" \
  -H "X-Vault-Namespace: admin" \
  -H "X-Vault-Request: true" \
  $VAULT_ADDR/v1/pki_int/cert/61:f6:7a:dd:71:d2:1c:c0:40:2e:58:cd:ef:d9:cb:6e:15:38:10:08 | jq ".data.certificate" -r | openssl x509 -text -noout


## Extract the issuer_id from above output and query the issuer
curl -s \
  -H "X-Vault-Token: $VAULT_TOKEN" \
  -H "X-Vault-Namespace: admin" \
  -H "X-Vault-Request: true" \
  $VAULT_ADDR/v1/pki_int/issuer/342cc192-ca6c-a41e-04cc-81499b21d49d | 


curl -s \
  -H "X-Vault-Token: $VAULT_TOKEN" \
  -H "X-Vault-Namespace: admin" \
  -H "X-Vault-Request: true" \
  -X POST \
  -d '{"input": "test.example.com"}' \
  $VAULT_ADDR/v1/sys/audit-hash/hcp-main-audit


## CloudWatch log filter examples

{ ($.request.operation = "update") && ($.request.path = "pki_int/issue/*") && ($.request.data.common_name = "hmac-sha256:8fb636b6bdda464c01bf791dbf06e67ac47a4345f79ff8acecbb9e6b6e1287fe")  && ($.response.data.expiration > 0) }

{ ($.request.operation = "update") && ($.request.path = "pki_int/issue/*") && ($.request.data.common_name = "hmac-sha256:77cb73cbefd1788d7196df8f83fe9923cf850b869030d96697d85860ccbbf9d5")  && ($.auth.entity_id != "") && ($.response.data.expiration != "__CLOUDWATCH_KEY_EXISTS_CHECK_PLACEHOLDER__") }

{ (($.request.path = "pki_int/revoke") && ($.request.data.serial_number = "hmac-sha256:77457198eb4b4ffbecc499d0c6db0e9cce4020b994e5ef383e622e94a63877f8") && ($.auth.entity_id != "") && ($.response.mount_type = "pki")) || (($.request.path = "pki_int/issue/*") && ($.response.data.serial_number = "hmac-sha256:77457198eb4b4ffbecc499d0c6db0e9cce4020b994e5ef383e622e94a63877f8") && ($.auth.entity_id != ""))}