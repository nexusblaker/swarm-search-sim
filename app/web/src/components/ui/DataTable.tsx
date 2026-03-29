export function DataTable({
  columns,
  rows,
}: {
  columns: string[];
  rows: Array<Array<React.ReactNode>>;
}) {
  return (
    <div className="scrollbar-subtle overflow-x-auto">
      <table className="min-w-full border-separate border-spacing-0 overflow-hidden text-sm">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column} className="border-b border-border bg-surfaceAlt px-4 py-3 text-left font-medium text-muted">
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {row.map((cell, cellIndex) => (
                <td key={`${rowIndex}-${cellIndex}`} className="border-b border-border/70 px-4 py-3 text-white">
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
