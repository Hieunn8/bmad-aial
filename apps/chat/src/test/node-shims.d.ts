declare module 'fs' {
  export function readFileSync(path: string | URL, encoding: string): string;
}
