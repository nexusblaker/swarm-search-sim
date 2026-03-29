export function ErrorState({ message }: { message: string }) {
  return (
    <div className="rounded-[28px] border border-danger/25 bg-danger/10 p-5 text-sm text-[#ecd6d9]">
      <p className="section-kicker text-danger">Something needs attention</p>
      <p className="mt-2 leading-6">{message}</p>
    </div>
  );
}
