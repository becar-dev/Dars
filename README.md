# Printshop + Stationery Mini-CRM Telegram Bot

Localda ishlaydigan aiogram 3.x bot. Yangi arxitektura: `orders` + `order_items` + katalog jadvallari.

## Asosiy imkoniyatlar

- Inline menyu (uz-Latn):
  - ➕ Yangi mijoz
  - 📊 Bugungi statistika
  - 📅 Haftalik statistika
  - 📦 Hisobot (xizmat/mahsulot)
- Bitta buyurtmaga bir nechta item qo‘shish (FSM)
- Xizmat va kantselyariya katalogi
- Adminlar katalogga yangi item qo‘sha oladi (`ADMIN_IDS`)
- `TelegramBadRequest: message is not modified` xatosi xavfsiz ignor qilinadi
- SQLite bazasi lokal faylda (`crm.db`)

## Loyiha tuzilmasi

```text
Dars/
├── app/
│   ├── config.py
│   ├── db/
│   │   └── database.py
│   ├── handlers/
│   │   └── bot.py
│   ├── keyboards/
│   │   └── inline.py
│   ├── states/
│   │   └── customer_flow.py
│   └── utils/
│       └── middlewares.py
├── migrations/
│   └── 001_orders_refactor.sql
├── .env.example
├── main.py
└── requirements.txt
```

## DB sxema

### `orders`
- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `created_at DATETIME DEFAULT CURRENT_TIMESTAMP`
- `status TEXT` (`asked_price|ordered|urgent|returned`)
- `customer_type TEXT` (`walk_in|returning`)
- `total_amount INTEGER DEFAULT 0`

### `order_items`
- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `order_id INTEGER NOT NULL`
- `category TEXT` (`service|stationery`)
- `item_name TEXT NOT NULL`
- `quantity INTEGER NOT NULL`
- `unit_price INTEGER NOT NULL`
- `line_total INTEGER NOT NULL`
- `FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE`

### `catalog_services`
### `catalog_products`
- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `name TEXT UNIQUE NOT NULL`
- `is_active INTEGER DEFAULT 1`

## Migratsiya (eski `customers_log` -> yangi sxema)

1. Dastur ishga tushganda `Database._initialize()` yangi jadvallarni yaratadi.
2. Agar `customers_log` mavjud bo‘lsa va hali migratsiya qilinmagan bo‘lsa:
   - Har bir eski qator `orders` ga bitta order bo‘lib yoziladi.
   - Har bir orderga `order_items` ga bitta item yoziladi (`category='service'`).
   - `migration_meta.legacy_customers_log_migrated=1` belgisi qo‘yiladi.
3. Eski `customers_log` jadvali saqlab qolinadi (audit/backward check uchun).
4. Qo‘shimcha SQL fayl: `migrations/001_orders_refactor.sql`.

## Ishga tushirish (Python 3.12+)

1) Virtual environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

2) Kutubxonalar:

```bash
pip install -r requirements.txt
```

3) `.env` tayyorlash:

```bash
cp .env.example .env
```

`.env` ichida:

```env
BOT_TOKEN=123456:YOUR_TELEGRAM_TOKEN
DB_PATH=crm.db
ADMIN_IDS=123456789
```

4) Botni ishga tushirish:

```bash
python main.py
```

## Validatsiya qoidalari

- Miqdor/narx maydonlari faqat raqam
- Manfiy qiymat taqiqlanadi
- `quantity` kamida `1`
- `0` qiymat faqat `asked_price` holatida ruxsat etiladi
- qolgan holatlarda 0 qiymat tanlansa statusni o'zgartirish talab qilinadi
