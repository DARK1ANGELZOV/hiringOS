# Killer Features Roadmap (15+)

Ниже список ключевых продуктовых функций для уровня «10/10» по ТЗ. Для каждой фичи указаны ценность, реализация и текущий статус.

| # | Фича | Ценность для бизнеса | Тех. реализация | Статус |
|---|------|----------------------|-----------------|--------|
| 1 | AI Parsing Resume (PDF/DOCX → JSON) | Ускоряет первичную обработку резюме | `POST /resumes/upload/{candidate_id}` + MinIO + ai-service | Implemented |
| 2 | Editable AI Autofill Resume | Контроль качества данных без потери скорости | `GET/PATCH /resumes/...` + frontend JSON editor | Implemented |
| 3 | Zero-Wait AI Interview Flow | Нет задержек для кандидата, лучше UX конверсия | `POST /interviews/{id}/answer` + async celery scoring | Implemented |
| 4 | Video Frame Ingestion for Interview | Аналитика по видео-сигналам кандидата | `POST /interviews/{id}/video/frame` | Implemented |
| 5 | Anti-Cheat Risk Scoring | Снижает риск читинга, повышает доверие HR | signals + aggregate score + risk levels | Implemented |
| 6 | Live Interview Monitoring | HR/руководитель видят онлайн-сессию | `GET /interviews/{id}/live` + WS channel | Implemented |
| 7 | Async AI Report for HR | Решение по кандидату с детальной аналитикой | `GET /interviews/{id}/report` (pending/ready/failed/partial) | Implemented |
| 8 | Semantic Candidate Search | Поиск по смыслу, не по ключевым словам | embeddings + `POST /candidates/search` | Implemented |
| 9 | Role-Based Route Security in UI | Снижение ошибок доступа и утечек | auth-context + backend RBAC | Implemented |
|10 | Knowledge Tests (algorithms/theory/product) | Массовый скрининг до собеседования | `/tests` CRUD + attempts + scoring | Implemented |
|11 | AI-Generated Tests | Быстрый запуск новых тестовых треков | `POST /tests/generate` | Implemented |
|12 | Custom Company Tests by Leads | Кастомизация процесса под каждую команду | `POST /tests` + company scope | Implemented |
|13 | Interview Question Bank by Stage | Управляемое качество вопросов интервью | `/interviews/question-bank` + `/tests/question-bank` | Implemented |
|14 | Full Audit Trail | Прозрачность и комплаенс | admin audit endpoints + event logs | Implemented |
|15 | Notification Center | Контроль SLA по этапам найма | `/notifications` + unread/read states | Implemented |
|16 | Candidate Status Pipeline | Управляемый pipeline найма | status transitions + history in backend | Implemented |
|17 | Degraded Mode Fallbacks (AI down) | Устойчивость процесса найма | partial analysis + non-blocking interview | Implemented |
|18 | Vacancy-Driven Interview Configuration | Привязка интервью к вакансии и стеку | `/admin/vacancies` + interview creation flow | Implemented |

## Что нужно сделать для финального «10/10»

1. Добавить backend endpoint управления пользователями (list/disable/role update) для полного IAM в admin/users.
2. Добавить e2e-тесты UI сценариев (Playwright) для Candidate/HR/Manager/Admin.
3. Включить обязательный HTTPS termination и CSP/HSTS в production reverse proxy.
4. Добавить observability stack (Prometheus + Grafana + Loki + alerts).
5. Формализовать policy-consent экран для anti-cheat и мониторинга до старта интервью.
6. Расширить voice/video pipeline на уровне браузерной диагностики устройств (mic/cam readiness).
7. Добавить API контракт-тесты (OpenAPI schema checks) в CI.

## Текущий уровень готовности

- Core ATS + AI Interview + Anti-Cheat + Tests + Admin Analytics: готово для pilot/production-hardening.
- Рекомендуемая оценка готовности после текущего цикла: **8.7/10**.
