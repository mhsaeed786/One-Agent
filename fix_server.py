path = 'server.ts'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
print('Total lines:', len(lines))
corrupted = [i for i, l in enumerate(lines) if "import express from 'express';``n" in l]
print('Corrupted start line:', corrupted[0] if corrupted else 'None')
if corrupted:
    idx = corrupted[0]
    clean = lines[:idx]
    while clean and clean[-1].strip() == '' and len(clean) > 1 and clean[-2].strip() == '':
        clean.pop()
    clean.append('\n')
    clean.append('// Start Server async wrapper to support Vite dev server middleware\n')
    clean.append('async function startServer() {\n')
    clean.append("  if (process.env.NODE_ENV !== 'production') {\n")
    clean.append("    const { createServer: createViteServer } = await import('vite');\n")
    clean.append('    const vite = await createViteServer({\n')
    clean.append('      server: { middlewareMode: true },\n')
    clean.append("      appType: 'spa',\n")
    clean.append('    });\n')
    clean.append('    app.use(vite.middlewares);\n')
    clean.append('  } else {\n')
    clean.append("    const distPath = path.join(process.cwd(), 'dist');\n")
    clean.append('    app.use(express.static(distPath));\n')
    clean.append("    app.get('*', (_req, res) => {\n")
    clean.append("      res.sendFile(path.join(distPath, 'index.html'));\n")
    clean.append('    });\n')
    clean.append('  }\n')
    clean.append('\n')
    clean.append("  app.listen(PORT, '0.0.0.0', () => {\n")
    clean.append('    console.log(`[OneAgent Super-App Server] Running at http://0.0.0.0:${PORT}`);\n')
    clean.append('  });\n')
    clean.append('}\n')
    clean.append('\n')
    clean.append('startServer();\n')
    with open(path, 'w', encoding='utf-8') as f:
        f.writelines(clean)
    print('Repaired. New line count:', len(clean))
