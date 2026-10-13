/// <reference types="node" />
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import ts from "typescript";

function routeFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) return routeFiles(path);
    return /\.[jt]sx?$/.test(entry.name) && !entry.name.endsWith(".d.ts") ? [path] : [];
  });
}

const routes = routeFiles(join(__dirname, "app"));

test("Expo Router does not expose test modules as routes", () => {
  expect(routes.filter((path) => /\.(test|spec)\.[jt]sx?$/.test(path))).toEqual([]);
});

test.each(routes.filter((path) => !/\+api\.[jt]s$/.test(path)))(
  "Expo Router screen %s exports a default component",
  (path) => {
    const source = ts.createSourceFile(path, readFileSync(path, "utf8"), ts.ScriptTarget.Latest, true);
    const hasDefaultExport = source.statements.some((statement) => {
      if (ts.isExportAssignment(statement)) return !statement.isExportEquals;
      if (ts.canHaveModifiers(statement) && ts.getModifiers(statement)?.some(
        (modifier) => modifier.kind === ts.SyntaxKind.DefaultKeyword,
      )) return true;
      return ts.isExportDeclaration(statement) && statement.exportClause
        && ts.isNamedExports(statement.exportClause)
        && statement.exportClause.elements.some((element) => element.name.text === "default");
    });
    expect(hasDefaultExport).toBe(true);
  },
);
