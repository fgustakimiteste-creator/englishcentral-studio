from pathlib import Path
p = Path('/app/mobile_app.py')
s = p.read_text(encoding='utf-8')
old = """        cookie_profile = read_public_cookie(request)
        token = expected if cookie_profile == profile_id else request.headers.get('x-ec-token', '')
        if not expected or not token or not hmac.compare_digest(token, expected):
"""
new = """        cookie_profile = read_public_cookie(request)
        print(f"[PUBLIC-SESSION] profile={profile_id} cookie_present={bool(request.cookies.get(PUBLIC_COOKIE))} cookie_profile={cookie_profile!r} token_file={bool(expected)}", flush=True)
        token = expected if cookie_profile == profile_id else request.headers.get('x-ec-token', '')
        if not expected or not token or not hmac.compare_digest(token, expected):
"""
if old not in s:
    raise SystemExit('Public profile auth block not found')
p.write_text(s.replace(old, new, 1), encoding='utf-8')
