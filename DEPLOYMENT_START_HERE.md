# 🚀 JanSamadhan AI Service — Railway Deployment Test Package

**Package Version:** 1.0  
**Created:** March 27, 2026  
**Status:** Ready for Standalone Deployment Testing

---

## 📌 Quick Context

This package contains **YOLO pothole detection AI microservice** that runs **independently** on Railway. It does NOT depend on the frontend or main backend being ready.

**Purpose of this test:** Verify the ONNX model loads correctly and inference works end-to-end.

**Timeline:** Can be deployed immediately while frontend/backend integration happens in parallel.

---

## 📦 Package Contents

```
ai-service-deploy/
├── DEPLOYMENT_START_HERE.md   ← Read this first!
├── requirements.txt            ← Python dependencies
├── models/
│   └── best.onnx              ← YOLO ONNX model (100 MB)
├── service/
│   ├── main.py                ← FastAPI app entry point
│   ├── onnx_inference_service.py  ← YOLO inference engine
│   ├── supabase_client.py     ← Database client (for later)
│   └── cctv_handler.py        ← Video processing (for later)
└── .env.example               ← Environment template
```

---

## ⚡ 30-Second Quick Start

### On Railway Dashboard:

1. **Create New Service** → Upload this ZIP
2. **Runtime:** Python 3.10+
3. **Start Command:**
   ```bash
   uvicorn service.main:app --host 0.0.0.0 --port $PORT
   ```
4. **Add Variables** (see below)
5. **Deploy** → Wait 3–5 min
6. **Test:** Hit `/health` endpoint

### Environment Variables (add in Railway):

```env
CONF_THRESHOLD=0.35
IMGSZ=640
DEVICE=0
```

---

## ✅ Success Criteria

### Test 1: Service Starts
Check Railway **Logs** → See:
```
INFO: Initializing detector signal from /app/models/best.onnx
```

### Test 2: Health Check Passes
```bash
curl https://<your-railway-url>/health
```

Returns:
```json
{"ok": true, "model_version": "v2.0-stable", "status": "ready"}
```

### Test 3: Inference Works
Upload a pothole image → Get detections back with confidence scores

---

## 🚨 Common Issues & Fixes

| Issue | Fix |
|---|---|
| `ModuleNotFoundError: ultralytics` | Requirements.txt not at root. Re-extract ZIP properly. |
| Health check returns `ok: false` | Model file missing. Check `/app/models/best.onnx` exists. |
| Inference timeout (>60s) | Cold start on Railway. Wait. Next inference will be fast. |
| GPU memory error | Set `DEVICE=cpu` in env variables. |

**If stuck:** Check Railway **Build Logs** and **Runtime Logs** tabs.

---

## 📡 Available Endpoints

All endpoints require `X-API-KEY` header except `/health`:

| Endpoint | Method | Test Command |
|---|---|---|
| `/health` | GET | `curl https://your-url/health` |
| `/analyze/image` | POST | `curl -X POST https://your-url/analyze/image -H "X-API-KEY: test-key" -F "image=@pothole.jpg"` |

---

## 🔑 Next Steps After Successful Test

1. ✅ Confirm service URL (e.g., `https://ai-service-abc123.railway.app`)
2. ✅ Set permanent `X-API-KEY` in env vars
3. ✅ Share URL + API-KEY with backend team
4. ✅ Backend team integrates this service into main `/apps/api`
5. ✅ Frontend will trigger video analysis → backend calls this service

**Until then:** This service is fully standalone and production-ready for testing.

---

## 📊 Architecture Context

```
JanSamadhan System:

┌─────────────────┐
│   Web Frontend  │ (Next.js 15)
│  (localhost:3000)
└────────┬────────┘
         │
         ▼
┌─────────────────────────────┐
│   Main FastAPI Backend      │ (apps/api)
│  (apps/api/main.py)         │
└────────┬────────────────────┘
         │ Calls for pothole detection
         ▼
┌─────────────────────────────┐
│  AI Service (THIS SERVICE)  │ ◄─── YOU ARE HERE
│  (ai-service/main.py)       │
│  • YOLO Inference           │
│  • FastAPI ✅               │
│  • ONNX Model ✅            │
│  • Fully Independent ✅     │
└─────────────────────────────┘
```

**This service can be tested independently** without the main backend running.

---

## 🔐 Security Notes

- Change `X-API-KEY` from default before production
- CORS is currently `"*"` — will be restricted before go-live
- Model file is 100 MB — Railway free tier may take time on first pull

---

## 📞 Who to Contact

- **If deployment fails:** Check Railway logs, then contact DevOps team
- **If model loading fails:** Verify `best.onnx` is 50–150 MB
- **If inference is slow:** That's expected on cold start. Subsequent calls are fast.

---

## ✨ You're All Set!

Extract this ZIP, follow the Quick Start above, and you should see `/health` return `ok: true` within 5 minutes of deployment.

**Good luck! 🚀**
