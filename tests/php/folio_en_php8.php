<?php
// Simula \DB::table('dato_seguimiento') con filas en memoria (id, nombre, valor).
class Q { public $rows; function __construct($r){$this->rows=$r;}
  function where($c,$op,$v=null){ if($v===null){$v=$op;$op='=';}
    $this->rows=array_values(array_filter($this->rows,function($r)use($c,$op,$v){
      if($op==='like'){ $re='/^'.str_replace('%','.*',preg_quote($v,'/')).'$/'; $re=str_replace('\.\*','.*',$re); return preg_match($re,$r[$c]); }
      return $r[$c]==$v; })); return $this; }
  function orderBy($c,$d){ usort($this->rows,function($a,$b)use($c,$d){return $d==='desc'?$b[$c]<=>$a[$c]:$a[$c]<=>$b[$c];}); return $this; }
  function lockForUpdate(){ return $this; }
  function value($c){ return $this->rows ? $this->rows[0][$c] : null; } }
class DB { static $filas=[]; static function table($t){ return new Q(self::$filas); } }
$codigo=json_decode(file_get_contents('/w/codigo.json'),true);
$casos=[
 'tabla vacia'=>[],
 'otro tramite ya uso numero_folio'=>[['id'=>1,'nombre'=>'numero_folio','valor'=>'CNIVA-2026-00003']],
 'ya hay GPM-2026-00007 (valor JSON con comillas)'=>[['id'=>1,'nombre'=>'numero_folio','valor'=>'CNIVA-2026-00003'],['id'=>2,'nombre'=>'numero_folio','valor'=>'"GPM-2026-00007"']],
 'folio de otro anio'=>[['id'=>1,'nombre'=>'numero_folio','valor'=>'GPM-2025-00090']],
];
foreach($codigo as $forma=>$php){ foreach($casos as $nombre=>$filas){ DB::$filas=$filas;
  try { $r=(function(){ return eval(func_get_arg(0)); })($php); echo str_pad($forma,6)," | ",str_pad($nombre,48)," => ",var_export($r,true),"\n"; }
  catch(\Throwable $e){ echo str_pad($forma,6)," | ",str_pad($nombre,48)," => ERROR ",get_class($e),": ",$e->getMessage(),"\n"; } } }
