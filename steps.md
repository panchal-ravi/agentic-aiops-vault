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
vault write pki_int/issue/example-dot-com common_name="test.example.com" ttl="24h"

vault write pki_int/revoke serial_number="61:f6:7a:dd:71:d2:1c:c0:40:2e:58:cd:ef:d9:cb:6e:15:38:10:08"

vault write pki_int/tidy tidy_cert_store=true tidy_revoked_certs=true

## List certs
v list pki/certs
v list pki_int/certs

v read -format=json pki/cert/48:60:17:61:21:f0:85:0d:c1:56:50:de:1c:12:dd:1a:5d:2b:ed:f0  | jq '.data.certificate' -r | openssl x509 -text -noout
v read -format=json pki/cert/29:67:5f:17:c0:2b:dd:e2:e0:d0:03:1d:79:be:b2:35:f2:55:99:de  | jq '.data.certificate' -r | openssl x509 -text -noout

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
  $VAULT_ADDR/v1/pki_int/cert/61:f6:7a:dd:71:d2:1c:c0:40:2e:58:cd:ef:d9:cb:6e:15:38:10:08 | jq .



## Extract the issuer_id from above output and read the Issuer who issued the above certificate
curl -s \
  -H "X-Vault-Token: $VAULT_TOKEN" \
  -H "X-Vault-Namespace: admin" \
  -H "X-Vault-Request: true" \
  $VAULT_ADDR/v1/pki_int/issuer/8eedc725-2f47-941c-1b28-e200211b4e0e | jq .
