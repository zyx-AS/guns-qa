import path from 'node:path';

export function env(name: string, fallback = ''): string {
  return (process.env[name] || fallback).trim();
}

export function requiredEnv(name: string): string {
  const fallback = name === 'APP_PASSWORD' ? '123456' : '';
  const value = env(name, fallback);
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

export function joinUrl(baseURL: string, pathname: string): string {
  return new URL(pathname, baseURL).toString();
}

export function selector(name: string, fallback: string): string {
  return env(name, fallback);
}

export function fixture(relativePath: string): string {
  return path.resolve(process.cwd(), relativePath);
}
