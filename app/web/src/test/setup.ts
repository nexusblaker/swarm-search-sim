import "@testing-library/jest-dom";

Object.defineProperty(HTMLCanvasElement.prototype, "getContext", {
  writable: true,
  value: () =>
    ({
      fillRect: () => undefined,
      strokeRect: () => undefined,
      beginPath: () => undefined,
      arc: () => undefined,
      fill: () => undefined,
      clearRect: () => undefined,
    }) as Partial<CanvasRenderingContext2D>,
});
