#!/usr/bin/env python3
"""
Extractor v5.3 - Cliente input + SL/SLU + LIMPIEZA INICIAL \\n?
"""

import argparse
import re
import pandas as pd
from pathlib import Path
import sys
from typing import Dict, Optional
from datetime import datetime

try:
    import fitz
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

def limpiar_texto_inicial(texto: str) -> str:
    """Descartar TODO ANTES del primer '\\n?' o '\\n'"""
    patron_inicio = r'\\n\?|\\n|\n\?'
    match = re.search(patron_inicio, texto)
    
    if match:
        texto_limpio = texto[match.end():].strip()
        return texto_limpio
    return texto.strip()

def extraer_texto_completo(pdf_path: Path) -> str:
    """Extracción + LIMPIEZA INICIAL"""
    if not PYMUPDF_AVAILABLE:
        print("⚠️ Instala: pip install PyMuPDF")
        return ""
    try:
        doc = fitz.open(pdf_path)
        texto = ""
        for page in doc:
            texto += page.get_text() + "\n"
        doc.close()
        
        # 🔥 NUEVO: Limpiar texto basura inicial
        texto_limpio = limpiar_texto_inicial(texto)
        return texto_limpio
    except:
        return ""

def normalizar_numero(numero: str) -> str:
    return re.sub(r'[^\w\-]', '', str(numero).strip()) if numero else ""

def normalizar_fecha(fecha: str) -> str:
    if not fecha: return ""
    fecha = re.sub(r'[^\d/.-]', '', fecha)[:10]
    return fecha

def normalizar_importe(importe: str) -> Optional[float]:
    if not importe: return None
    importe = re.sub(r'[€EUR\s€]', '', str(importe).strip())
    importe = re.sub(r'[^\d.,]', '', importe.replace(',', '.'))
    try: return float(importe)
    except: return None

def extraer_proveedor_por_SL(texto: str) -> str:
    """Texto ANTES de SL/SLU/S.L."""
    patrones_SL = [
        r'([A-ZÁÉÍÑÓÚ][a-záéíñóú]+(?:\s+[A-ZÁÉÍÑÓÚ][a-záéíñóú]+)*?)\s*[.,]?\s*(?:S\.?L\.?(?:\.?U\.?)?)',
        r'([A-ZÁÉÍÑÓÚ][a-záéíñóú]+(?:\s+[A-ZÁÉÍÑÓÚ][a-záéíñóú]+)*?)\s+(?:S\.?L\.?(?:\.?U\.?)?)',
        r'([A-ZÁÉÍÑÓÚ][a-záéíñóú]{2,}(?:\s+[A-ZÁÉÍÑÓÚ][a-záéíñóú]+)*?)\s*,\s*S\.?L\.?(?:\.?U\.?)?',
    ]
    for patron in patrones_SL:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            return match.group(1).strip()[:80]
    return ""

def extraer_proveedor_cliente_por_bloques(texto: str, nombre_cliente: str) -> Dict[str, str]:
    print(f"    👤 Cliente: '{nombre_cliente}'")
    
    # PRIORIDAD 1: SL/SLU
    proveedor_sl = extraer_proveedor_por_SL(texto)
    if proveedor_sl:
        print(f"    💼 Proveedor SL: {proveedor_sl}")
        return {"cliente": nombre_cliente.strip()[:80], "proveedor": proveedor_sl}
    
    # PRIORIDAD 2: NIF
    nif_match = re.search(r'(?:CIF|NIF)\s*[:\-]?\s*([A-Z]\d{8}[A-Z0-9]?)', texto, re.IGNORECASE)
    if nif_match:
        print(f"    💼 Proveedor NIF: {nif_match.group(1)}")
        return {"cliente": nombre_cliente.strip()[:80], "proveedor": nif_match.group(1)}
    
    print("    ⚠️ Proveedor no detectado")
    return {"cliente": nombre_cliente.strip()[:80], "proveedor": "N/D"}

def extraer_importes_universal(texto: str) -> Dict[str, Optional[float]]:
    zona_resumen = texto[-3000:]
    patrones = [
        (r'(?:Total\s*(?:factura|a pagar|final|en EUR)?|TOTAL|Importe total)\s*[:\-\(\)]*\s*([\d.,]+)', 'total'),
        (r'TOTAL\s*[:\-\(\)]*\s*([\d.,]+)', 'total'),
        (r'(?:Base\s*(?:imponible|imp\.?)|Subtotal|IMPORTE\s*\(base imponible\))\s*[:\-\(\)]*\s*([\d.,]+)', 'base_imponible'),
        (r'base imponible\).*?([\d.,]+)', 'base_imponible'),
        (r'(?:IVA?|I\.V\.A\.?|IMPUESTOS\s*\(21|Cuota IVA)\s*[:\-\(\)]*\s*([\d.,]+)', 'iva'),
        (r'Total\s*\(base imponible\).*?([\d.,]+)', 'base_imponible'),
        (r'Subtotal en EUR.*?([\d.,]+)', 'base_imponible'),
    ]
    
    resultado = {'total': None, 'base_imponible': None, 'iva': None}
    for patron, campo in patrones:
        if resultado[campo] is not None: continue
        match = re.search(patron, zona_resumen, re.IGNORECASE | re.DOTALL)
        if match:
            valor = normalizar_importe(match.group(1))
            if valor: resultado[campo] = valor
    return resultado

def extraer_datos_factura_completo(texto: str, nombre_fichero: str, nombre_cliente: str) -> Dict:
    datos = {
        'numero_factura': '', 'fecha_factura': '', 'proveedor': '', 'cliente': '',
        'base_imponible': None, 'iva': None, 'total': None, 'nombre_fichero': nombre_fichero
    }
    
    # Número factura
    numero_match = (re.search(r'N(?:\.°|º)?\s*de?\s*factura\s*[:\-]?\s*(\w+)', texto) or 
                    re.search(r'Número\s*[:\-]?\s*(\w+)', texto))
    datos['numero_factura'] = normalizar_numero(numero_match.group(1)) if numero_match else nombre_fichero.replace('.pdf', '')
    
    # Fecha
    fecha_match = re.search(r'Fecha\s+de?\s*(?:factura|facturación|emisión)\s*[:\-]?\s*([\d/\.-]{8,10})', texto, re.IGNORECASE)
    if not fecha_match:
        fecha_match = re.search(r'\b(\d{1,2}[/\.-]\d{1,2}[/\.-]\d{2,4})\b', texto)
    datos['fecha_factura'] = normalizar_fecha(fecha_match.group(1)) if fecha_match else ""
    
    # Importes
    importes = extraer_importes_universal(texto)
    datos.update(importes)
    
    # Proveedor + Cliente
    contacto = extraer_proveedor_cliente_por_bloques(texto, nombre_cliente)
    datos['cliente'] = contacto['cliente']
    datos['proveedor'] = contacto['proveedor']
    
    return datos

def main():
    parser = argparse.ArgumentParser(description='Extractor v5.3 - LIMPIEZA \\n?')
    parser.add_argument('carpeta_pdf', help='Carpeta PDFs')
    parser.add_argument('-o', '--output', help='CSV salida')
    args = parser.parse_args()
    
    carpeta = Path(args.carpeta_pdf)
    if not carpeta.exists():
        print(f"❌ Carpeta no existe: {carpeta}")
        sys.exit(1)
    
    # Input cliente
    try:
        print("👤 IDENTIFICACIÓN")
        nombre_cliente = input("Nombre del cliente tal como aparece: ").strip()
    except KeyboardInterrupt:
        print("\n👋 Cancelado")
        sys.exit(0)
    
    if not nombre_cliente:
        print("❌ Cliente requerido")
        sys.exit(1)
    
    print(f"\n🚀 v5.3 - Cliente: '{nombre_cliente}' - LIMPIEZA \\n?")
    
    filas, procesados = [], 0
    
    for pdf_path in carpeta.glob("*.pdf"):
        print(f"\n📄 {pdf_path.name}")
        procesados += 1
        
        texto = extraer_texto_completo(pdf_path)
        if not texto.strip():
            print("   ❌ SIN TEXTO")
            continue
        
        datos = extraer_datos_factura_completo(texto, pdf_path.name, nombre_cliente)
        filas.append(datos)
        
        # FIX TypeError None
        total_val = datos.get('total')
        total_str = f"{total_val:.2f}" if total_val is not None else "N/D"
        print(f"   ✅ Total: €{total_str} | Proveedor: {datos.get('proveedor', 'N/D')}")
    
    if not filas:
        print("❌ Sin PDFs válidos")
        sys.exit(1)
    
    df = pd.DataFrame(filas)
    columnas = ['numero_factura', 'fecha_factura', 'proveedor', 'cliente', 
                'base_imponible', 'iva', 'total', 'nombre_fichero']
    df = df[columnas]
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = args.output or f"facturas_v53_{nombre_cliente}_{timestamp}.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    print(f"\n🎉 COMPLETADO! {len(filas)}/{procesados}")
    print(f"💾 {output_file}")
    
    con_total = df['total'].notna().sum()
    print(f"📊 Totales: {con_total}/{len(df)} ({con_total/len(df)*100:.1f}%)")
    
    print("\n📋 PREVIA:")
    print(df[['proveedor', 'cliente', 'total', 'nombre_fichero']].to_string(index=False))

if __name__ == "__main__":
    sys.exit(main())
