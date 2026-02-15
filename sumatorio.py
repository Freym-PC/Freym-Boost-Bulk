#!/usr/bin/env python3
"""
SUMADOR CSV v1.1 - IGNORA texto/vacías AUTOMÁTICO
python sumador_csv.py archivo.csv 3 --debug
"""

import argparse
import pandas as pd
import sys

def sumar_columna_csv(archivo_csv: str, num_columna: int, debug: bool = False):
    try:
        # Leer CSV flexible
        df = pd.read_csv(archivo_csv)
        
        if debug:
            print("📊 ARCHIVO:", archivo_csv)
            print("📈 COLUMNAS:", list(df.columns))
            print("🔢 COLUMNA:", num_columna, df.columns[num_columna])
            print("\n📋 PREVIA 10 FILAS:")
            print(df.iloc[:, num_columna].head(10))
        
        # VALIDAR COLUMNA
        if num_columna < 0 or num_columna >= len(df.columns):
            print(f"❌ Columna inválida (0-{len(df.columns)-1})")
            return None
        
        nombre_col = df.columns[num_columna]
        
        # 🔥 CONVERTIR A NÚMERICO - IGNORA TODO lo no numérico
        columna_original = df[nombre_col].astype(str)
        columna_numerica = pd.to_numeric(columna_original, errors='coerce')
        
        if debug:
            print(f"\n🔄 PROCESO columna '{nombre_col}':")
            print("Ejemplos ORIGINAL → NÚMERICO:")
            for i in range(min(5, len(df))):
                orig = columna_original.iloc[i]
                num = columna_numerica.iloc[i]
                print(f"  '{orig}' → {num}")
        
        # SUMA (NaN ignorados automáticamente)
        total_suma = columna_numerica.sum()
        
        # ESTADÍSTICAS DETALLADAS
        total_filas = len(df)
        filas_validas = columna_numerica.notna().sum()
        filas_invalidas = total_filas - filas_validas
        
        print("\n" + "="*60)
        print(f"🎯 COLUMNA: '{nombre_col}' (índice {num_columna})")
        print(f"📊 Filas total: {total_filas:,}")
        print(f"✅ Filas SUMADAS: {filas_validas:,}")
        print(f"❌ Filas IGNORADAS: {filas_invalidas:,}")
        print(f"💰 **TOTAL: {total_suma:,.2f}**")
        print("="*60)
        
        if debug:
            # MOSTRAR ejemplos ignorados
            indices_invalidos = columna_numerica[columna_numerica.isna()].index[:5]
            if len(indices_invalidos) > 0:
                print("\n🚫 EJEMPLOS IGNORADOS:")
                for idx in indices_invalidos:
                    print(f"  Fila {idx}: '{columna_original.iloc[idx]}'")
        
        return total_suma
        
    except FileNotFoundError:
        print(f"❌ No encontrado: {archivo_csv}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Sumador CSV - Ignora texto/vacías')
    parser.add_argument('archivo_csv', help='CSV archivo')
    parser.add_argument('columna', type=int, nargs='?', help='Columna índice (0-based)')
    parser.add_argument('-c', '--columna', type=int, help='Alternativa columna')
    parser.add_argument('-d', '--debug', action='store_true', help='Debug detallado')
    
    args = parser.parse_args()
    
    # Obtener columna
    num_columna = args.columna if args.columna is not None else args.columna
    if num_columna is None:
        print("❌ Uso: python sumador.py archivo.csv 3")
        print("   o: python sumador.py archivo.csv --columna 5 --debug")
        sys.exit(1)
    
    print("🚀 SUMADOR CSV v1.1 - Ignora texto/vacías")
    
    resultado = sumar_columna_csv(args.archivo_csv, num_columna, args.debug)
    
    if resultado is not None:
        print(f"\n✅ FINAL: **{resultado:,.2f}**")

if __name__ == "__main__":
    main()
