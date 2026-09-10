import { Button } from "@/components/ui/button";
import type { Hueco } from "@/lib/types";

/**
 * Control por defecto para cualquier hueco `falta_dato` sin control especifico:
 * un solo boton que marca el dato como "se configura a mano en la plataforma".
 */
export default function BotonReconocer({
  onReconocer,
}: {
  hueco: Hueco;
  onReconocer: () => void | Promise<void>;
}) {
  return (
    <Button type="button" variant="outline" onClick={() => onReconocer()}>
      Lo configuro a mano
    </Button>
  );
}
