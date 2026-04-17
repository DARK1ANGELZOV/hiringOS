import { expect, test } from '@playwright/test'

async function login(page: Parameters<typeof test>[0]['page'], email: string, password: string) {
  await page.goto('/login')
  await expect(page.getByRole('heading', { name: 'Вход в HiringOS' })).toBeVisible()
  await page.getByLabel('Эл. почта').fill(email)
  await page.getByLabel('Пароль').fill(password)
  await page.getByRole('button', { name: 'Войти' }).click()
}

test('публичные страницы авторизации на русском языке', async ({ page }) => {
  await page.goto('/login')
  await expect(page.getByRole('heading', { name: 'Вход в HiringOS' })).toBeVisible()
  await expect(page.getByText('Авторизуйтесь для работы с кандидатами и интервью')).toBeVisible()

  await page.goto('/register')
  await expect(page.getByRole('heading', { name: 'Регистрация в HiringOS' })).toBeVisible()
  await expect(page.getByText('Через открытую регистрацию создается только роль кандидата')).toBeVisible()
})

test('кандидат может зарегистрироваться через UI и попасть в dashboard', async ({ page, request }) => {
  const bootstrapNonce = Date.now()
  await request.post('http://localhost:8000/api/v1/auth/register', {
    data: {
      full_name: 'Bootstrap Owner',
      email: `bootstrap_${bootstrapNonce}@example.com`,
      password: 'StrongPass123!',
    },
  })

  const nonce = Date.now()
  const email = `e2e_candidate_${nonce}@example.com`
  const password = 'StrongPass123!'

  await page.goto('/register')
  await expect(page.getByRole('heading', { name: 'Регистрация в HiringOS' })).toBeVisible()
  await page.waitForTimeout(1200)
  await page.getByLabel('ФИО').fill('E2E Candidate')
  await page.getByLabel('Эл. почта').fill(email)
  await page.getByLabel('Пароль').fill(password)
  await page.getByRole('button', { name: 'Зарегистрироваться' }).click()

  await expect(page).toHaveURL(/\/candidate/)
  const greetingHeading = page.getByRole('heading', { name: /Здравствуйте,/i })
  const greetingVisible = await greetingHeading.isVisible().catch(() => false)
  if (!greetingVisible) {
    await expect(page.getByRole('heading', { name: 'Профиль кандидата не создан' })).toBeVisible()
  }
})

test('HR dashboard доступен для HR аккаунта', async ({ page }) => {
  const email = process.env.E2E_HR_EMAIL
  const password = process.env.E2E_HR_PASSWORD
  test.skip(!email || !password, 'Set E2E_HR_EMAIL and E2E_HR_PASSWORD to run HR flow')

  await login(page, email as string, password as string)
  await expect(page).toHaveURL(/\/hr/)
})

test('Manager dashboard доступен для Manager аккаунта', async ({ page }) => {
  const email = process.env.E2E_MANAGER_EMAIL
  const password = process.env.E2E_MANAGER_PASSWORD
  test.skip(!email || !password, 'Set E2E_MANAGER_EMAIL and E2E_MANAGER_PASSWORD to run manager flow')

  await login(page, email as string, password as string)
  await expect(page).toHaveURL(/\/manager/)
})

test('Admin IAM страница доступна для Admin аккаунта', async ({ page }) => {
  const email = process.env.E2E_ADMIN_EMAIL
  const password = process.env.E2E_ADMIN_PASSWORD
  test.skip(!email || !password, 'Set E2E_ADMIN_EMAIL and E2E_ADMIN_PASSWORD to run admin flow')

  await login(page, email as string, password as string)
  await page.goto('/admin/users')
  await expect(page.getByRole('heading', { name: 'Пользователи и роли' })).toBeVisible()
})
