export function DataTable({
  columns,
  rows,
}: {
  columns: string[];
  rows: Array<Array<React.ReactNode>>;
}) {
  return (
    <div className="scrollbar-subtle overflow-x-auto rounded-[24px] border border-border/70 bg-surfaceAlt/25">
      <table className="min-w-full border-separate border-spacing-0 overflow-hidden text-sm">
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column}
                className="border-b border-border/70 bg-surfaceAlt/80 px-5 py-3.5 text-left text-[11px] font-medium uppercase tracking-[0.18em] text-muted"
              >
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex} className="transition hover:bg-white/[0.02]">
              {row.map((cell, cellIndex) => (
                <td
                  key={`${rowIndex}-${cellIndex}`}
                  className="border-b border-border/60 px-5 py-4 align-top leading-6 text-white"
                >
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
