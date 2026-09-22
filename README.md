# Hermes Agent → Aquera API Integration

Integrasi resmi **Hermes AI Agent** dengan platform akuakultur **Aquera** melalui API layer, dirancang untuk eksekusi lokal dan deployment siap pakai di **AWS Bedrock AgentCore Runtime**.

---

## 🏛️ Arsitektur Sistem

```text
User / WhatsApp / Client
          │
          ▼
    Hermes Agent
          │
    ┌─────┴────────────────┐
    ▼                      ▼
LLM Provider          Aquera API
(OpenRouter/Bedrock)  (/api/v1/*)
                           │
                           ▼
                     Aquera Backend
                           │
                           ▼
                     Database (Supabase)
```

### Prinsip Utama
1. **Pemisahan Tanggung Jawab**: Hermes bertindak sebagai reasoning agent dan orchestrator tool; logika bisnis, otorisasi, dan database transaction tetap berada di Aquera API.
2. **Server-Side RBAC Enforcement**: Otorisasi diverifikasi di layer integrasi (`enforce_permission`) sebelum request HTTP dikirim ke backend Aquera. LLM **tidak pernah** menentukan hak akses pengguna.
3. **No Hardcoded Secrets**: Kredensial dan token API dioper melalui environment variable atau AWS Secrets Manager.
4. **Safe Retries**: Hanya read-operation (GET) yang di-retry pada error transient (429, 500, 502, 503, 504). Operasi mutasi (POST) tidak pernah di-retry secara buta.
5. **Upstream Compatibility**: Modul integrasi ditempatkan terisolasi di `integrations/aquera/` dan `agentcore/` agar fork Hermes mudah disinkronkan dengan repository original.

---

## 📂 Struktur Direktori

```text
hermes/
├── hermes/                    # Hermes agent core & tool registry
│   ├── __init__.py
│   ├── agent.py
│   └── registry.py
├── integrations/
│   └── aquera/                # Modul integrasi Aquera
│       ├── __init__.py
│       ├── client.py          # Async httpx client dengan safe retry & headers
│       ├── auth.py            # RBAC policy terpusat (owner, admin, manager, staff, viewer)
│       ├── models.py          # Data models & mutation validation
│       ├── errors.py          # Typed error hierarchy & status code mapping
│       └── tools.py           # Pre-authorized Aquera tools
├── agentcore/                 # AWS Bedrock AgentCore runtime layer
│   ├── __init__.py
│   ├── app.py                # HTTP runtime contract (/invocations & /ping)
│   └── config.py             # Typed environment configuration
├── tests/
│   ├── test_aquera_client.py # Client & retry unit tests
│   ├── test_aquera_tools.py  # Pre-authorization & validation tests
│   └── test_rbac.py          # Role matrix tests
├── .env.example
├── Dockerfile
├── pyproject.toml
└── README.md
```

---

## 🚀 Setup Lokal

### 1. Prasyarat
- Python 3.10+
- Aquera Next.js backend berjalan (`npm run dev`) di port 3000

### 2. Instalasi Dependensi
```bash
cd hermes
pip install -e ".[dev]"
```

### 3. Konfigurasi Environment
Salin `.env.example` menjadi `.env`:
```bash
cp .env.example .env
```
Isi variabel:
```env
OPENROUTER_API_KEY=sk-or-v1-...
AQUERA_BASE_URL=http://localhost:3000
AQUERA_API_TOKEN=your_aquera_api_secret
DEFAULT_ORGANIZATION_ID=your-organization-uuid
```

### 4. Menjalankan Unit Tests
```bash
pytest tests/ -v
```

### 5. Menjalankan AgentCore Server Lokal
```bash
python -m agentcore.app
```
Server akan aktif di `http://0.0.0.0:8080`.

Test endpoint ping:
```bash
curl http://localhost:8080/ping
```

Test invocations:
```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"message": "Tampilkan ringkasan panen terbaru", "role": "admin"}'
```

---

## 🐳 Docker Deployment

Build image Docker:
```bash
docker build -t hermes-aquera:latest .
```

Jalankan container:
```bash
docker run -d \
  --name hermes-agent \
  -p 8080:8080 \
  --env-file .env \
  hermes-aquera:latest
```

---

## ☁️ AWS Bedrock AgentCore Deployment

1. **Amazon ECR**: Push container image ke ECR repository.
2. **Bedrock AgentCore Runtime**: Daftarkan runtime container mengarah ke image ECR.
3. **IAM Least Privilege**: Runtime hanya memerlukan izin membaca secret di AWS Secrets Manager (`AQUERA_API_TOKEN`, `OPENROUTER_API_KEY`) dan publish CloudWatch Logs.
4. **Invocation Flow**: Event invocation dari WhatsApp/Client akan memicu endpoint `POST /invocations` yang menjalankan reasoning Hermes dan integrasi Aquera.
