# Flora — multilingual Django flower shop

Flora is a working local flower-shop application using **Python, Django 5.2, Django REST Framework, Django templates, CSS and vanilla JavaScript**. There is no React, Node application server, Firebase, AI model or external SMS service. The generated hero image is a static asset; Flower Finder itself only uses deterministic catalog filters.

## Tez boshlash (Windows)

Loyiha papkasida PowerShell oching:

```powershell
cd C:\Users\User\Desktop\flower-shop
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py createcachetable
.\.venv\Scripts\python.exe manage.py seed_demo
.\.venv\Scripts\python.exe manage.py create_admin --email admin@example.test --name "Shop owner"
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Open **http://127.0.0.1:8000/**. On this delivered workspace the database, sample catalog, local assets and virtual environment are already initialized. Do not overwrite an existing .env when following the fresh-install example. No administrator with a published/default password is installed. The create_admin command asks for a password privately and validates it.

For subsequent runs, use `powershell -File .\start.ps1` or the runserver command above. The existing local preview process writes to `logs/server.log` and `logs/server-error.log`; its PID is in `logs/server.pid`. Stop that specific process before starting another server on port 8000.

On Linux/macOS replace the Python executable with `.venv/bin/python`. Python 3.11+ recommended.

## Workspaces and behavior

- Public page: story, collections, benefits, ordering process, delivery FAQ, contacts at the bottom.
- Customer: /workspace/dashboard/, shop, product details, favorites filter, collections, cart, checkout, order history/details, messages, profile, addresses, settings.
- Custom administrator: /manage/overview/, products, categories, variants/inventory, orders, customers, conversations, notifications, editable guide configuration, profile and settings.
- Optional maintenance tool: /maintenance/ (superuser access).
- /auth/ always asks for a language first. Admin is a login choice; public registration cannot grant staff or superuser privileges.
- Existing account language/theme are restored on login. Guests use local storage; account preferences are stored in the database. Checkout fields survive language changes.
- All UI text comes from static/i18n.js (English, Uzbek, Russian). Translated catalog content is stored as JSON with English fallback. Django LocaleMiddleware/gettext serve authentication/reset/confirmation content. Run `python tools/compile_translations.py` after translating shared messages; it regenerates editable .po and compiled .mo catalogs.
- Images and SVG flags/icons are local. See ASSETS.md for sources, licenses and the generated-image prompt.

## Purchase and inventory rules

Currency defaults to UZS and delivery costs 25,000 UZS, configured with SHOP_CURRENCY and SHOP_DELIVERY_FEE. The sample catalog and sample guide budgets are denominated in UZS; update both prices and guide budget labels/rules when switching currency. Demo imagery and catalog are explicitly labeled demonstration content.

Each product supports translated names, description and care, category, color, occasion, flower type, image, archive state, and multiple translated size variants with their own decimal prices and stock. Add a product, then create at least one active variant to make it purchasable. Public catalog filtering combines search, category, occasion, color, stock and price on matching variants. Favorites persist per user.

The persistent cart is account-scoped (sign in before shopping). Quantities must be whole numbers from 1 to 99 and cannot exceed stock. All line prices, totals and delivery charges are recalculated on the server. Browser totals and unauthorized profile fields are ignored.

Checkout accepts recipient, phone, address, date, time slot, gift message and notes. Delivery dates run from tomorrow through 30 days ahead, using Asia/Tashkent server time. Slots are configured in settings.DELIVERY_SLOTS. Delivery coverage/business details require the owner to configure or confirm them; no real address or telephone was invented.

Orders and immutable translated line-price snapshots are created in a single transaction. Conditional stock updates prevent negative inventory. PostgreSQL row locks serialize account checkout and inventory access; SQLite uses IMMEDIATE transactions plus conditional updates. A unique UUID submission key makes retries idempotent. The cart clears only after successful creation.

Cash on delivery works by default. There are no fake card fields or simulated card charges. Payment state is separate from delivery state. Administrators can explicitly mark delivered COD orders paid; collected revenue includes only delivered **and paid** orders. Discounts and online payment providers are not configured.

Allowed order transitions:
- pending → confirmed or cancelled
- confirmed → preparing or cancelled
- preparing → out_for_delivery or cancelled
- out_for_delivery → delivered
- delivered / cancelled are terminal

Cancellation restores stock at most once. Delivered orders are not cancellable through this workflow. Refunds/returns and integrated card payments are outside the configured COD workflow.

## Messages and Flower Finder

An order creates a persistent notification for each active administrator at the time of placement. Status changes notify the customer. In-app “SMS” means these website notifications, not telephone messages.

Conversation subjects can reference a product or the customer's own order. Customer and seller messages are persisted and escaped, with a 2,000-character limit. Conversations are owner-scoped; staff can reply to customers. Notifications and unread counts poll every 12 seconds while the tab is visible. Conversation history is paginated with older-message loading. No WebSocket service is needed.

Flower Finder reads core.GuideConfig. Steps accept only occasion, color, flower_type or max_price; their choices have translated labels and prepared responses. Answers become filters on real, active, available catalog variants. Back, restart, broader search, prepared FAQs and contact-seller actions work. Administrators can edit the validated JSON configuration from their custom panel.

## Accounts and security

Django session authentication, password hashing and CSRF protection protect same-origin requests. Anonymous login/registration/reset POSTs are explicitly CSRF protected. Login/registration/reset attempts have shared database-backed IP and account counters (20 attempts per 15 minutes). API endpoints also have DRF request throttles.

Email changes require the current password and a one-hour signed confirmation link sent to the new email. Until confirmed, the old login email remains active. The link is bound to the old email and password hash and is invalidated by changes. Password reset uses Django's token/password validation facilities; password change requires the current password.

Default development email is printed to the server console/log. To actually deliver reset and verification emails, configure an SMTP backend and credentials in .env:
`EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`, EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD and a verified DEFAULT_FROM_EMAIL.

Profiles support name, phone, avatar upload/removal, language and theme. Avatars and catalog uploads accept validated JPEG, PNG and WebP, up to 5 MB and 16 megapixels. Upload filenames are replaced with UUIDs. Replaced/deleted avatars are removed after transaction commit.

Account deletion requires a current-password confirmation. It deletes the account, addresses, cart, favorites and owned conversations, anonymizes recipient/phone/address/gift notes on retained orders, and retains financial line-item snapshots. Related staff notifications show the anonymized recipient. Avatar files are removed. The last active staff account cannot delete itself. Set a real retention policy for your business before handling actual customer data.

Referenced products/categories are archived by API delete actions. Order snapshots and history survive archival. Staff access is enforced on backend endpoints; selecting “Admin” in the UI never changes roles.

## Testing

Backend regression suite:

```powershell
.\.venv\Scripts\python.exe manage.py test core.tests
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
```

Isolated headless browser acceptance test (uses a disposable database, test-only accounts and a separate browser profile):

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe manage.py test core.browser_tests --settings=config.test_settings
```

It uses installed Microsoft Edge by default. For Chrome set `$env:BROWSER_CHANNEL='chrome'`. No real customer data, external email, orders or payments are used. Screenshots are saved under test-artifacts/. The test checks language-first registration, catalog filters, guided selection, cart quantity edits, checkout language preservation, order confirmation, seller inbox/status changes, customer/seller messages, profile/address CRUD, dark theme/language persistence, unauthorized access, mobile overflow and drawer behavior.

See VERIFICATION.md for the actual recorded results and limits of verification.

## Data and project layout

- accounts/: custom User, saved addresses, avatar lifecycle.
- catalog/: category, product, size variants, favorites.
- orders/: account carts, orders and snapshot lines.
- messaging/: conversations, messages, order notifications.
- core/: validated DRF serializers/endpoints, web/auth views, guide configuration, commands/tests.
- config/: environment-based Django settings, URL routing and WSGI.
- templates/, static/, locale/: reusable shell, focused views, local assets, CSS, vanilla JS and translations.
- fixtures/demo_catalog.json: translated sample catalog and guide; use `seed_demo` on an empty catalog or `loaddata fixtures/demo_catalog.json` on an empty database, not both on an existing catalog.
- Migrations are committed for every model. seed_demo is idempotent and does not create fake metrics, orders or customer accounts.

API collections are paginated (24 items/page). Main routes include /api/products/, /api/categories/, /api/variants/, /api/cart/, /api/checkout/, /api/orders/, /api/conversations/, /api/notifications/, /api/profile/, /api/addresses/, /api/guide/, /api/dashboard/, /api/customers/, /api/password/ and /api/email/. Mutating session-authenticated requests require X-CSRFToken. API errors use an error object and translated client messages.

## Production setup

This deliverable is running locally, not published to a hosting provider. A Python/WSGI-compatible host is needed. Do not run Django's development server in production.

1. Install requirements; use DB_ENGINE=postgresql with POSTGRES_* variables. PostgreSQL support is configured but needs your database and has not been exercised in this local SQLite environment.
2. Set DJANGO_DEBUG=0, a cryptographically random DJANGO_SECRET_KEY, correct DJANGO_ALLOWED_HOSTS and HTTPS DJANGO_CSRF_TRUSTED_ORIGINS. The app refuses production startup without a secret. .env is excluded from source control.
3. Configure SMTP, shop contact placeholders, currency/delivery policy and real catalog/inventory.
4. Run migrate, createcachetable and collectstatic. Create the owner using create_admin.
5. Run a production WSGI server, e.g. `waitress-serve --listen=127.0.0.1:8000 config.wsgi:application`, behind an HTTPS reverse proxy.
6. Serve STATIC_ROOT under /static/ and MEDIA_ROOT under /media/ with the proxy/storage layer. Treat media as untrusted, never executable. Do not expose the project directory or .env.
7. If TLS terminates at a trusted reverse proxy, configure SECURE_PROXY_SSL_HEADER only after the proxy strips any client-provided forwarded-protocol header. Secure cookies, HSTS, SSL redirect, content-type sniffing protection and frame denial are enabled in production.
8. Restrict /maintenance/, add backups, monitoring and infrastructure-level rate limiting. Run `manage.py check --deploy` under the production environment.

Production integrations requiring owner configuration: public hosting/domain/TLS, PostgreSQL service, SMTP, real shop details and delivery coverage, optional payment provider. Local COD, internal notifications and conversations need no external credentials.

