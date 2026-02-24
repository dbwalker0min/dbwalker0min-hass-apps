$token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJlNDE1NWZhN2Y5MDg0ZmM0ODA4ZjU4MjYwMjE2ODEwOCIsImlhdCI6MTc3MTQ1NTMxMCwiZXhwIjoyMDg2ODE1MzEwfQ.gupiOJ3BY0OFbWhERXMiZ2x1ecoedy0Y6ZQEZW3fkbg"

$ha = "http://ha.home:8123"   # or https://...
$headers = @{ Authorization = "Bearer $token" }

# Equivalent to "Check for updates" in the add-on store
Invoke-RestMethod -Method Post -Uri "$ha/api/hassio/store/reload" -Headers $headers | Out-Null