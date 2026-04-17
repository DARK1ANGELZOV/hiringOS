import fs from 'node:fs'
import path from 'node:path'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const projectRoot = path.resolve(__dirname, '..')

const ensureStub = (relativePath) => {
  const absolutePath = path.join(projectRoot, relativePath)
  fs.mkdirSync(path.dirname(absolutePath), { recursive: true })
  if (!fs.existsSync(absolutePath)) {
    fs.writeFileSync(absolutePath, 'export {}\n', 'utf-8')
  }
}

ensureStub('.next/types/validator.ts')
ensureStub('.next/dev/types/validator.ts')

const tscBin = path.join(projectRoot, 'node_modules', 'typescript', 'bin', 'tsc')
const result = spawnSync(process.execPath, [tscBin, '--noEmit'], {
  cwd: projectRoot,
  stdio: 'inherit',
})

process.exit(result.status ?? 1)

