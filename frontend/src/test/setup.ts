import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { toast } from "sonner";

// jsdom no implementa `matchMedia` y `sonner` lo consulta al montarse para
// resolver el tema. Sin este stub, cualquier prueba que renderice el `Toaster`
// revienta con "window.matchMedia is not a function".
if (!window.matchMedia) {
  window.matchMedia = (query: string): MediaQueryList =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }) as unknown as MediaQueryList;
}

// La cola de `sonner` es un singleton de modulo: sobrevive al desmontaje del
// `Toaster` y se filtra a la prueba siguiente, que entonces encuentra dos
// toasts con el mismo texto. Se vacia al terminar cada prueba.
afterEach(() => {
  toast.dismiss();
});
