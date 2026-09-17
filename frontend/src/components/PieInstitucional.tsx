/**
 * La greca que cierra la página, la misma de los PDF de la Dirección.
 *
 * Es un `background` repetido, no un `<img>`: así se adapta a cualquier ancho
 * sin deformarse y sin cargar una imagen de 2048px para pintar una franja. El
 * archivo viene recortado a su contenido y con el mismo margen transparente a
 * cada lado, que es lo que hace que empalme sin costura al repetirse — el PNG
 * original salía del PDF con márgenes desiguales y se veía la unión.
 *
 * Decorativa: `aria-hidden`, porque no dice nada que no esté ya escrito.
 */
export default function PieInstitucional() {
  return (
    <div
      data-slot="greca"
      aria-hidden="true"
      className="h-6 shrink-0 bg-repeat-x"
      style={{ backgroundImage: "url('/greca.png')", backgroundSize: "auto 100%" }}
    />
  );
}
