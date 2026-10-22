from pathlib import Path
import secrets
p = Path('.env')
if p.exists():
    raise SystemExit('Existing .env preserved')
s = Path('.env.example').read_text()
s = s.replace('REPLACE_WITH_RANDOM_SECRET', secrets.token_hex(32)).replace('REPLACE_WITH_DIFFERENT_RANDOM_SECRET', secrets.token_hex(32)).replace('REPLACE_WITH_RANDOM_PASSWORD', secrets.token_hex(24))
p.write_text(s)
p.chmod(0o600)
print('Created .env with generated secrets (not displayed)')
