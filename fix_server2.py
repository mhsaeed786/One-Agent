path = 'server.ts'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix 1: JSON.stringify(input or {}) -> JSON.stringify(input ?? {})
for i, line in enumerate(lines):
    if 'JSON.stringify(input or {})' in line:
        lines[i] = line.replace('JSON.stringify(input or {})', 'JSON.stringify(input ?? {})')
        print('Fixed or -> ?? at line', i+1)

# Fix 2: arguments = {} -> args = {} (reserved word in ESM)
for i, line in enumerate(lines):
    if 'const { tool_name, arguments = {} } = req.body;' in line:
        lines[i] = line.replace('arguments = {}', 'args = {}')
        print('Fixed arguments -> args at line', i+1)

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Done')
