export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-4xl items-center px-6 py-16 sm:px-12">
      <section className="w-full rounded-3xl border border-surface bg-white p-8 shadow-sm sm:p-14">
        <p className="inline-block rounded-full bg-blush px-4 py-2 text-sm font-semibold text-burgundy">
          Part 1 · Project setup
        </p>
        <h1 className="mt-6 max-w-xl text-4xl font-semibold tracking-tight sm:text-6xl">
          Sephora Business Insight
        </h1>
        <p className="mt-5 max-w-lg leading-relaxed">
          A business intelligence workspace for Sephora product and customer review analytics.
        </p>
      </section>
    </main>
  );
}
