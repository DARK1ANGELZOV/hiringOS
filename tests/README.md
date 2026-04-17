# Quality Test Suite

## E2E (Playwright)

```bash
cd tests/e2e
npm install
npm run install:browsers
npm test
```

Environment variables:

- `E2E_BASE_URL` (default `http://localhost:3000`)
- `E2E_HR_EMAIL` / `E2E_HR_PASSWORD` (optional)
- `E2E_MANAGER_EMAIL` / `E2E_MANAGER_PASSWORD` (optional)
- `E2E_ADMIN_EMAIL` / `E2E_ADMIN_PASSWORD` (optional)

If role-specific credentials are not provided, role tests are skipped and public/candidate flows still run.

## Load Testing

### k6

```bash
k6 run tests/load/k6-smoke.js
```

Optional auth load:

```bash
K6_ENABLE_AUTH_FLOW=true k6 run tests/load/k6-smoke.js
```

Optional base URL:

```bash
K6_BASE_URL=http://localhost:8000 k6 run tests/load/k6-smoke.js
```

### Locust

```bash
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

