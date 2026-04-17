import http from 'k6/http'
import { check, sleep } from 'k6'

const baseUrl = __ENV.K6_BASE_URL || 'http://localhost:8000'
const enableAuthFlow = (__ENV.K6_ENABLE_AUTH_FLOW || 'false').toLowerCase() === 'true'

export const options = {
  scenarios: {
    health: {
      executor: 'ramping-vus',
      startVUs: 1,
      stages: [
        { duration: '30s', target: 10 },
        { duration: '1m', target: 30 },
        { duration: '30s', target: 0 },
      ],
      gracefulRampDown: '10s',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.02'],
    http_req_duration: ['p(95)<800'],
  },
}

function randomEmail() {
  return `load_${Date.now()}_${Math.floor(Math.random() * 1_000_000)}@example.com`
}

export default function () {
  const health = http.get(`${baseUrl}/healthz`)
  check(health, {
    'healthz is 200': (r) => r.status === 200,
  })

  const ready = http.get(`${baseUrl}/readyz`)
  check(ready, {
    'readyz is 200': (r) => r.status === 200,
  })

  if (enableAuthFlow) {
    const registerPayload = JSON.stringify({
      full_name: 'K6 Candidate',
      email: randomEmail(),
      password: 'StrongPass123!',
    })
    const register = http.post(`${baseUrl}/api/v1/auth/register`, registerPayload, {
      headers: { 'Content-Type': 'application/json' },
    })
    check(register, {
      'register status is 201': (r) => r.status === 201,
    })

    if (register.status === 201) {
      const body = register.json()
      const token = body?.access_token
      if (token) {
        const me = http.get(`${baseUrl}/api/v1/auth/me`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        })
        check(me, {
          'auth /me status is 200': (r) => r.status === 200,
        })
      }
    }
  }

  sleep(1)
}

