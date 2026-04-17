import os
import re
import pickle
import requests
from threading import Lock

BASE_URL = "https://adtelecom.sgp.net.br"
LOGIN_URL = f"{BASE_URL}/accounts/login/?next=/admin/"
ADMIN_URL = f"{BASE_URL}/admin/"
COOKIES_FILE = os.getenv("COOKIES_FILE", "sgp_cookies.pkl")

SGP_USER = os.getenv("SGP_USER")
SGP_PASS = os.getenv("SGP_PASS")

_cookie_lock = Lock()

def extract_csrf_from_login(html: str) -> str:
    m = re.search(
        r'name=[\'"]csrfmiddlewaretoken[\'"][^>]*value=[\'"]([^\'"]+)[\'"]',
        html,
        flags=re.IGNORECASE
    )
    if not m:
        raise RuntimeError("CSRF do login não encontrado no HTML.")
    return m.group(1)

def save_cookies(session: requests.Session) -> None:
    with _cookie_lock:
        with open(COOKIES_FILE, "wb") as f:
            pickle.dump(session.cookies, f)

def load_cookies(session: requests.Session) -> bool:
    if not os.path.exists(COOKIES_FILE):
        return False
    with _cookie_lock:
        with open(COOKIES_FILE, "rb") as f:
            session.cookies.update(pickle.load(f))
    return True

def is_logged_in(session: requests.Session) -> bool:
    r = session.get(ADMIN_URL, timeout=20, allow_redirects=True)
    return "/accounts/login" not in r.url

def do_login(session: requests.Session) -> None:
    if not SGP_USER or not SGP_PASS:
        raise RuntimeError("SGP_USER/SGP_PASS não definidos nas variáveis de ambiente.")

    session.headers.update({"User-Agent": "Mozilla/5.0"})

    # GET login page
    r_get = session.get(LOGIN_URL, timeout=20)
    r_get.raise_for_status()
    csrf = extract_csrf_from_login(r_get.text)

    # POST login
    payload = {
        "username": SGP_USER,
        "password": SGP_PASS,
        "csrfmiddlewaretoken": csrf,
        "next": "/admin/",
    }
    headers = {"Referer": LOGIN_URL, "Origin": BASE_URL}

    r_post = session.post(LOGIN_URL, data=payload, headers=headers, timeout=20, allow_redirects=True)
    r_post.raise_for_status()

    if not is_logged_in(session):
        snippet = r_post.text[:300].replace("\n", " ")
        raise RuntimeError(f"Login no SGP falhou (ainda cai no login). Trecho: {snippet}")

    save_cookies(session)

def get_session_logged() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0"})

    load_cookies(s)

    if not is_logged_in(s):
        do_login(s)

    return s

def disconnect(contrato_id: str) -> dict:
    s = get_session_logged()

    url = f"{BASE_URL}/admin/servicos/internet/{contrato_id}/disconnect/"

    r = s.get(url, headers={"Referer": ADMIN_URL}, timeout=20, allow_redirects=True)

    # Se caiu no login, reloga e tenta 1x
    if "/accounts/login" in r.url:
        do_login(s)
        r = s.get(url, headers={"Referer": ADMIN_URL}, timeout=20, allow_redirects=True)

    # resultado
    if "/accounts/login" in r.url:
        return {"ok": False, "reason": "sessao_invalida", "final_url": r.url, "status": r.status_code}

    return {"ok": r.status_code in (200, 302), "status": r.status_code, "final_url": r.url}

def add_cliente_contact(
    cliente_id: str,
    contato: str,
    tipo: str = "WHATSAPP",
    inscricoes: tuple[int, ...] = (15, 16, 32, 33, 34),
    observacao: str = "Contato atualizado pelo WPP IA",
) -> dict:
    s = get_session_logged()
    edit_url = f"{BASE_URL}/admin/cliente/{cliente_id}/edit/"
    post_url = f"{BASE_URL}/admin/contato/add/cliente/{cliente_id}/"

    def fetch_csrf_tokens() -> tuple[str, str]:
        r_edit = s.get(edit_url, headers={"Referer": ADMIN_URL}, timeout=20, allow_redirects=True)
        if "/accounts/login" in r_edit.url:
            do_login(s)
            r_edit = s.get(edit_url, headers={"Referer": ADMIN_URL}, timeout=20, allow_redirects=True)
        r_edit.raise_for_status()

        cookie_csrf = s.cookies.get("csrftoken", "")
        form_csrf = ""
        try:
            form_csrf = extract_csrf_from_login(r_edit.text)
        except RuntimeError:
            pass

        if not form_csrf:
            form_csrf = cookie_csrf
        if not form_csrf:
            raise RuntimeError("CSRF nao encontrado para cadastrar contato.")
        if not cookie_csrf:
            cookie_csrf = form_csrf

        return form_csrf, cookie_csrf

    form_csrf, cookie_csrf = fetch_csrf_tokens()

    payload = [
        ("csrfmiddlewaretoken", form_csrf),
        ("tipo", tipo),
        ("contato", contato),
    ]
    for inscricao in inscricoes:
        payload.append(("inscricoes", str(inscricao)))
    payload.append(("observacao", observacao))

    headers = {
        "Referer": edit_url,
        "Origin": BASE_URL,
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": cookie_csrf,
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }
    r_post = s.post(post_url, data=payload, headers=headers, timeout=20, allow_redirects=True)

    if "/accounts/login" in r_post.url:
        do_login(s)
        form_csrf, cookie_csrf = fetch_csrf_tokens()
        payload[0] = ("csrfmiddlewaretoken", form_csrf)
        headers["X-CSRFToken"] = cookie_csrf
        r_post = s.post(post_url, data=payload, headers=headers, timeout=20, allow_redirects=True)

    if "/accounts/login" in r_post.url:
        return {"ok": False, "reason": "sessao_invalida", "final_url": r_post.url, "status": r_post.status_code}

    if r_post.status_code == 404:
        raise RuntimeError(
            f"Rota de contato retornou 404 no SGP: {post_url}. "
            f"Verifique se o cliente_id {cliente_id} existe e se o usuario tem permissao."
        )

    if r_post.status_code >= 400:
        snippet = r_post.text[:300].replace("\n", " ")
        raise RuntimeError(f"Falha ao cadastrar contato no SGP ({r_post.status_code}). Trecho: {snippet}")

    return {"ok": r_post.status_code in (200, 201, 204, 302), "status": r_post.status_code, "final_url": r_post.url}
