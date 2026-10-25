import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <main className="relative flex min-h-screen items-center justify-center bg-[#f8fafc] p-6 overflow-hidden">
      {/* Ambient background glow */}
      <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
        <div className="absolute -top-32 left-1/2 -translate-x-1/2 h-[500px] w-[600px] rounded-full bg-gradient-to-tr from-indigo-200/50 to-violet-200/40 blur-3xl" />
      </div>

      <SignUp
        appearance={{
          elements: {
            rootBox: "mx-auto",
            card: "rounded-3xl shadow-2xl shadow-indigo-500/10 border border-slate-200/80 backdrop-blur-xl bg-white/95",
            primaryButton: "bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl shadow-sm",
          },
        }}
        path="/sign-up"
        routing="path"
        signInUrl="/sign-in"
      />
    </main>
  );
}
