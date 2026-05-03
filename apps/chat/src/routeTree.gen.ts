/* eslint-disable */

// @ts-nocheck

// This file is auto-generated in spirit, but checked in here as a minimal
// route tree so plain `tsc --noEmit` has the same path knowledge as Vite.

import { Route as rootRouteImport } from './routes/__root'
import { Route as AuthCallbackRouteImport } from './routes/auth/callback'
import { Route as IndexRouteImport } from './routes/index'
import { Route as LoginRouteImport } from './routes/login'

export interface FileRoutesByFullPath {
  '/': typeof IndexRoute
  '/login': typeof LoginRoute
  '/auth/callback': typeof AuthCallbackRoute
}

export interface FileRoutesByTo {
  '/': typeof IndexRoute
  '/login': typeof LoginRoute
  '/auth/callback': typeof AuthCallbackRoute
}

export interface FileRoutesById {
  '__root__': typeof rootRouteImport
  '/': typeof IndexRoute
  '/login': typeof LoginRoute
  '/auth/callback': typeof AuthCallbackRoute
}

export interface FileRouteTypes {
  fileRoutesByFullPath: FileRoutesByFullPath
  fullPaths: '/' | '/login' | '/auth/callback'
  fileRoutesByTo: FileRoutesByTo
  to: '/' | '/login' | '/auth/callback'
  id: '__root__' | '/' | '/login' | '/auth/callback'
  fileRoutesById: FileRoutesById
}

export interface RootRouteChildren {
  indexRoute: typeof IndexRoute
  loginRoute: typeof LoginRoute
  authCallbackRoute: typeof AuthCallbackRoute
}

declare module '@tanstack/react-router' {
  interface FileRoutesByPath {
    '/': {
      id: '/'
      path: '/'
      fullPath: '/'
      preLoaderRoute: typeof IndexRouteImport
      parentRoute: typeof rootRouteImport
    }
    '/login': {
      id: '/login'
      path: '/login'
      fullPath: '/login'
      preLoaderRoute: typeof LoginRouteImport
      parentRoute: typeof rootRouteImport
    }
    '/auth/callback': {
      id: '/auth/callback'
      path: '/auth/callback'
      fullPath: '/auth/callback'
      preLoaderRoute: typeof AuthCallbackRouteImport
      parentRoute: typeof rootRouteImport
    }
  }
}

const IndexRoute = IndexRouteImport.update({
  id: '/',
  path: '/',
  getParentRoute: () => rootRouteImport,
} as any)

const LoginRoute = LoginRouteImport.update({
  id: '/login',
  path: '/login',
  getParentRoute: () => rootRouteImport,
} as any)

const AuthCallbackRoute = AuthCallbackRouteImport.update({
  id: '/auth/callback',
  path: '/auth/callback',
  getParentRoute: () => rootRouteImport,
} as any)

const rootRouteChildren: RootRouteChildren = {
  indexRoute: IndexRoute,
  loginRoute: LoginRoute,
  authCallbackRoute: AuthCallbackRoute,
}

export const routeTree = rootRouteImport
  ._addFileChildren(rootRouteChildren)
  ._addFileTypes<FileRouteTypes>()
