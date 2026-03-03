# Printshop + Kantselyariya Mini-CRM Bot (PostgreSQL)

## Talablar
- Python 3.12+
- aiogram 3.x
- PostgreSQL (Supabase yoki Neon)
- Google Cloud VM (systemd)

## Menyu (/start)
1. ➕ Yangi mijoz
2. 📊 7 kunlik statistika
3. 📊 30 kunlik statistika
4. 📈 To‘liq statistika
5. 📅 Sana bo‘yicha statistika

## Ishga tushirish
```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```

## .env
```env
BOT_TOKEN=...
DATABASE_URL=postgresql://user:password@host:5432/dbname
ADMIN_IDS=123456789,987654321
TZ=Asia/Tashkent
```

## PostgreSQL migratsiya
```bash
psql "$DATABASE_URL" -f migrations/002_postgres_microcrm.sql
```

## Google Cloud VM + systemd
```bash
sudo mkdir -p /opt/printshop-bot
# loyihani /opt/printshop-bot ga joylang
cd /opt/printshop-bot
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# .env ni to‘ldiring
sudo cp deploy/printshop-bot.service /etc/systemd/system/printshop-bot.service
sudo systemctl daemon-reload
sudo systemctl enable printshop-bot
sudo systemctl start printshop-bot
sudo systemctl status printshop-bot
journalctl -u printshop-bot -f
```

## Eslatma
- Barcha foydalanuvchi matnlari uzbek (uz-Latn).
- Adminlar katalog CRUD qila oladi, oddiy foydalanuvchilar faqat savdo/statistika.
- Sana guruhlash Asia/Tashkent bo‘yicha.
