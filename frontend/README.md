# SmartStudy - Frontend

A Next.js 15 application powering the SmartStudy interactive whiteboard platform, featuring Excalidraw, Clerk authentication, and real-time AI tutor interaction.

## Tech Stack

- **Framework**: Next.js 15 (App Router, React 19)
- **Styling**: Tailwind CSS
- **Whiteboard Engine**: Excalidraw
- **Auth**: Clerk (`@clerk/nextjs`)
- **State & Data Fetching**: TanStack React Query
- **Testing**: Vitest (contract & integration), Playwright (E2E)

## Getting Started

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

Required variables:
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`: Clerk publishable key
- `CLERK_SECRET_KEY`: Clerk secret key
- `NEXT_PUBLIC_API_URL`: Backend API base URL (default: `http://127.0.0.1:8000`)

### 3. Run Development Server

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser.

## Available Scripts

- `npm run dev` - Start development server on port 3000
- `npm run build` - Build production bundle
- `npm run start` - Start production server
- `npm run lint` - Run ESLint checks
- `npm run test` - Run Vitest contract and integration tests
- `npm run test:watch` - Run Vitest in interactive watch mode
- `npm run test:e2e` - Run Playwright end-to-end tests
