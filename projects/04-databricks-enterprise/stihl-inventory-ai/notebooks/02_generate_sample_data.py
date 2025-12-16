# Databricks notebook source
# MAGIC %md
# MAGIC # STIHL Inventory AI - Sample Data Generation
# MAGIC 
# MAGIC This notebook generates realistic sample data for the STIHL inventory analytics system.
# MAGIC 
# MAGIC **Data Generated:**
# MAGIC - ~100 products across categories (Chainsaws, Trimmers, Blowers, Hedge Trimmers, etc.)
# MAGIC - 24 months of historical sales data
# MAGIC - Daily inventory snapshots (current month)
# MAGIC - Realistic pricing, margins, and sales patterns

# COMMAND ----------

# MAGIC %pip install faker

# COMMAND ----------

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from datetime import datetime, timedelta
from decimal import Decimal
import random
import uuid

# Initialize Spark
spark = SparkSession.builder.getOrCreate()

# Configuration
CATALOG = "stihl"
SCHEMA_SILVER = "silver"
SCHEMA_GOLD = "gold"

# Date range for historical data
END_DATE = datetime.now().date()
START_DATE = END_DATE - timedelta(days=730)  # 24 months

print(f"Generating data from {START_DATE} to {END_DATE}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Product Master Data
# MAGIC 
# MAGIC Based on actual STIHL product categories and naming conventions.

# COMMAND ----------

# STIHL Product Catalog (based on real product research)
PRODUCTS = [
    # CHAINSAWS - Gas
    {"model": "MS 170", "name": "MS 170", "cat": "Chainsaws", "sub": "Gas Chainsaws", "power": "Gas", "segment": "Homeowner", "cc": 30.1, "bar": 16, "weight": 8.6, "msrp": 199.99, "cost": 95.00, "desc": "Lightweight entry-level chainsaw perfect for occasional use around the home.", "features": "IntelliCarb compensating carburetor,Easy-start system,Side-access chain tensioner"},
    {"model": "MS 180 C-BE", "name": "MS 180 C-BE", "cat": "Chainsaws", "sub": "Gas Chainsaws", "power": "Gas", "segment": "Homeowner", "cc": 31.8, "bar": 16, "weight": 9.3, "msrp": 279.99, "cost": 135.00, "desc": "Easy-to-start chainsaw with Quick Chain Adjuster for homeowner convenience.", "features": "Easy2Start system,Quick Chain Adjuster,Anti-vibration system"},
    {"model": "MS 250", "name": "MS 250", "cat": "Chainsaws", "sub": "Gas Chainsaws", "power": "Gas", "segment": "Homeowner", "cc": 45.4, "bar": 18, "weight": 10.1, "msrp": 349.99, "cost": 168.00, "desc": "Versatile mid-range chainsaw for demanding homeowner tasks.", "features": "Pre-separation air filter,IntelliCarb,Ematic lubrication system"},
    {"model": "MS 271", "name": "Farm Boss", "cat": "Chainsaws", "sub": "Gas Chainsaws", "power": "Gas", "segment": "Professional", "cc": 50.2, "bar": 20, "weight": 12.3, "msrp": 429.99, "cost": 215.00, "desc": "The Farm Boss MS 271 is a powerful mid-range chainsaw designed for demanding cutting tasks.", "features": "IntelliCarb compensating carburetor,Side-access chain tensioner,Pre-separation air filter"},
    {"model": "MS 291", "name": "MS 291", "cat": "Chainsaws", "sub": "Gas Chainsaws", "power": "Gas", "segment": "Professional", "cc": 55.5, "bar": 20, "weight": 12.8, "msrp": 479.99, "cost": 235.00, "desc": "Powerful all-around chainsaw for landowners and professionals.", "features": "Pre-separation air filter,IntelliCarb,Anti-vibration system,Ematic chain lubrication"},
    {"model": "MS 362 C-M", "name": "MS 362 C-M", "cat": "Chainsaws", "sub": "Gas Chainsaws", "power": "Gas", "segment": "Professional", "cc": 59.0, "bar": 20, "weight": 13.0, "msrp": 899.99, "cost": 450.00, "desc": "Professional-grade chainsaw with M-Tronic technology for optimal performance.", "features": "STIHL M-Tronic,HD2 air filter,Decompression valve,Side-access chain tensioner"},
    {"model": "MS 461", "name": "MS 461", "cat": "Chainsaws", "sub": "Gas Chainsaws", "power": "Gas", "segment": "Professional", "cc": 76.5, "bar": 25, "weight": 14.6, "msrp": 1099.99, "cost": 550.00, "desc": "High-performance professional chainsaw for the most demanding felling jobs.", "features": "Stratified charge engine,Decompression valve,HD2 filter,Anti-vibration"},
    {"model": "MS 500i", "name": "MS 500i", "cat": "Chainsaws", "sub": "Gas Chainsaws", "power": "Gas", "segment": "Professional", "cc": 79.2, "bar": 25, "weight": 13.9, "msrp": 1599.99, "cost": 800.00, "desc": "World's first chainsaw with electronically controlled fuel injection.", "features": "Fuel injection,STIHL M-Tronic,Captive bar nuts,HD2 filter"},
    
    # CHAINSAWS - Battery
    {"model": "MSA 60 C-B", "name": "MSA 60 C-B", "cat": "Chainsaws", "sub": "Battery Chainsaws", "power": "Battery", "segment": "Homeowner", "cc": None, "bar": 12, "weight": 5.5, "msrp": 199.99, "cost": 95.00, "desc": "Lightest battery chainsaw in the STIHL lineup for home use.", "features": "AK Battery System,Quick chain adjustment,Low kickback chain"},
    {"model": "MSA 120 C-B", "name": "MSA 120 C-B", "cat": "Chainsaws", "sub": "Battery Chainsaws", "power": "Battery", "segment": "Homeowner", "cc": None, "bar": 12, "weight": 6.2, "msrp": 279.99, "cost": 135.00, "desc": "Battery-powered chainsaw for light-duty cutting tasks around the home.", "features": "AK Battery System,Quick chain adjustment,Rubberized handle"},
    {"model": "MSA 140 C-B", "name": "MSA 140 C-B", "cat": "Chainsaws", "sub": "Battery Chainsaws", "power": "Battery", "segment": "Homeowner", "cc": None, "bar": 12, "weight": 6.4, "msrp": 349.99, "cost": 168.00, "desc": "Powerful battery chainsaw for firewood cutting and storm cleanup.", "features": "AK Battery System,Chain brake,Quick chain adjustment"},
    {"model": "MSA 161 T", "name": "MSA 161 T", "cat": "Chainsaws", "sub": "Battery Chainsaws", "power": "Battery", "segment": "Professional", "cc": None, "bar": 12, "weight": 5.7, "msrp": 449.99, "cost": 225.00, "desc": "Top-handled battery chainsaw for arborists and tree care professionals.", "features": "AP Battery System,Top handle,Chain brake"},
    {"model": "MSA 200 C-B", "name": "MSA 200 C-B", "cat": "Chainsaws", "sub": "Battery Chainsaws", "power": "Battery", "segment": "Professional", "cc": None, "bar": 14, "weight": 7.9, "msrp": 499.99, "cost": 250.00, "desc": "Professional battery chainsaw with excellent cutting performance.", "features": "AP Battery System,Quick chain adjustment,Chain brake"},
    {"model": "MSA 220 C-B", "name": "MSA 220 C-B", "cat": "Chainsaws", "sub": "Battery Chainsaws", "power": "Battery", "segment": "Professional", "cc": None, "bar": 16, "weight": 8.4, "msrp": 599.99, "cost": 300.00, "desc": "Powerful battery chainsaw with up to 40 minutes of run time.", "features": "AP Battery System,EC motor,Quick chain adjustment,Low kickback chain"},
    
    # TRIMMERS - Gas
    {"model": "FS 38", "name": "FS 38", "cat": "Trimmers", "sub": "Gas Trimmers", "power": "Gas", "segment": "Homeowner", "cc": 27.2, "bar": None, "weight": 9.3, "msrp": 159.99, "cost": 75.00, "desc": "Entry-level gas trimmer for homeowners with smaller yards.", "features": "TapAction bump head,Bike handle,Easy start"},
    {"model": "FS 56 RC-E", "name": "FS 56 RC-E", "cat": "Trimmers", "sub": "Gas Trimmers", "power": "Gas", "segment": "Homeowner", "cc": 27.2, "bar": None, "weight": 10.1, "msrp": 249.99, "cost": 120.00, "desc": "Reliable homeowner trimmer with Easy2Start technology.", "features": "Easy2Start,Simplified starting procedure,Bike handle,TapAction head"},
    {"model": "FS 91 R", "name": "FS 91 R", "cat": "Trimmers", "sub": "Gas Trimmers", "power": "Gas", "segment": "Professional", "cc": 28.4, "bar": None, "weight": 11.8, "msrp": 399.99, "cost": 195.00, "desc": "Professional-grade trimmer with low exhaust emissions.", "features": "4-MIX engine,Low emissions,Multi-function handle"},
    {"model": "FS 111 R", "name": "FS 111 R", "cat": "Trimmers", "sub": "Gas Trimmers", "power": "Gas", "segment": "Professional", "cc": 31.4, "bar": None, "weight": 11.7, "msrp": 449.99, "cost": 220.00, "desc": "Powerful professional trimmer with 4-MIX engine.", "features": "4-MIX engine,Bike handle,Anti-vibration system"},
    {"model": "FS 131 R", "name": "FS 131 R", "cat": "Trimmers", "sub": "Gas Trimmers", "power": "Gas", "segment": "Professional", "cc": 36.3, "bar": None, "weight": 12.1, "msrp": 499.99, "cost": 245.00, "desc": "High-performance brushcutter for demanding vegetation management.", "features": "4-MIX engine,Multi-function handle,Easy2Start"},
    
    # TRIMMERS - Battery
    {"model": "FSA 57", "name": "FSA 57", "cat": "Trimmers", "sub": "Battery Trimmers", "power": "Battery", "segment": "Homeowner", "cc": None, "bar": None, "weight": 5.7, "msrp": 169.99, "cost": 80.00, "desc": "Lightweight battery trimmer for small yard maintenance.", "features": "AK Battery System,AutoCut head,Adjustable shaft"},
    {"model": "FSA 60 R", "name": "FSA 60 R", "cat": "Trimmers", "sub": "Battery Trimmers", "power": "Battery", "segment": "Homeowner", "cc": None, "bar": None, "weight": 6.6, "msrp": 219.99, "cost": 105.00, "desc": "Versatile battery trimmer with bike handle for comfort.", "features": "AK Battery System,Bike handle,PolyCut head"},
    {"model": "FSA 90 R", "name": "FSA 90 R", "cat": "Trimmers", "sub": "Battery Trimmers", "power": "Battery", "segment": "Professional", "cc": None, "bar": None, "weight": 8.2, "msrp": 329.99, "cost": 160.00, "desc": "Professional battery trimmer with extended run time.", "features": "AP Battery System,EC motor,Bike handle"},
    {"model": "FSA 130 R", "name": "FSA 130 R", "cat": "Trimmers", "sub": "Battery Trimmers", "power": "Battery", "segment": "Professional", "cc": None, "bar": None, "weight": 8.8, "msrp": 449.99, "cost": 220.00, "desc": "Top-tier professional battery trimmer for all-day use.", "features": "AP Battery System,EC motor,Multi-function handle"},
    
    # BLOWERS - Gas
    {"model": "BG 50", "name": "BG 50", "cat": "Blowers", "sub": "Gas Blowers", "power": "Gas", "segment": "Homeowner", "cc": 27.2, "bar": None, "weight": 7.9, "msrp": 149.99, "cost": 70.00, "desc": "Entry-level handheld blower for light yard cleanup.", "features": "27.2cc engine,Adjustable tube,Easy start"},
    {"model": "BG 86 C-E", "name": "BG 86 C-E", "cat": "Blowers", "sub": "Gas Blowers", "power": "Gas", "segment": "Professional", "cc": 27.2, "bar": None, "weight": 9.9, "msrp": 299.99, "cost": 145.00, "desc": "Professional handheld blower with Easy2Start.", "features": "Easy2Start,High air velocity,Stop switch"},
    {"model": "BR 350", "name": "BR 350", "cat": "Blowers", "sub": "Gas Blowers", "power": "Gas", "segment": "Professional", "cc": 63.3, "bar": None, "weight": 22.5, "msrp": 399.99, "cost": 195.00, "desc": "Backpack blower for professional landscape maintenance.", "features": "Backpack design,Anti-vibration,Adjustable support harness"},
    {"model": "BR 450", "name": "BR 450", "cat": "Blowers", "sub": "Gas Blowers", "power": "Gas", "segment": "Professional", "cc": 63.3, "bar": None, "weight": 23.1, "msrp": 449.99, "cost": 220.00, "desc": "High-performance backpack blower for commercial use.", "features": "Backpack design,High air volume,Ergonomic harness"},
    {"model": "BR 600", "name": "BR 600", "cat": "Blowers", "sub": "Gas Blowers", "power": "Gas", "segment": "Professional", "cc": 64.8, "bar": None, "weight": 21.6, "msrp": 549.99, "cost": 270.00, "desc": "Most powerful backpack blower in the STIHL lineup.", "features": "64.8cc engine,677 CFM,Backpack frame,4-MIX engine"},
    {"model": "BR 800 C-E", "name": "BR 800 C-E", "cat": "Blowers", "sub": "Gas Blowers", "power": "Gas", "segment": "Professional", "cc": 79.9, "bar": None, "weight": 26.0, "msrp": 699.99, "cost": 345.00, "desc": "Ultimate backpack blower for the most demanding cleanup jobs.", "features": "79.9cc engine,Easy2Start,912 CFM,Telescoping tube"},
    
    # BLOWERS - Battery
    {"model": "BGA 57", "name": "BGA 57", "cat": "Blowers", "sub": "Battery Blowers", "power": "Battery", "segment": "Homeowner", "cc": None, "bar": None, "weight": 5.1, "msrp": 159.99, "cost": 75.00, "desc": "Compact battery blower for light yard maintenance.", "features": "AK Battery System,Variable speed,Lightweight"},
    {"model": "BGA 60", "name": "BGA 60", "cat": "Blowers", "sub": "Battery Blowers", "power": "Battery", "segment": "Homeowner", "cc": None, "bar": None, "weight": 5.5, "msrp": 199.99, "cost": 95.00, "desc": "Versatile battery blower with boost mode.", "features": "AK Battery System,Boost mode,Round nozzle"},
    {"model": "BGA 86", "name": "BGA 86", "cat": "Blowers", "sub": "Battery Blowers", "power": "Battery", "segment": "Professional", "cc": None, "bar": None, "weight": 7.3, "msrp": 329.99, "cost": 160.00, "desc": "Professional battery blower with excellent power-to-weight ratio.", "features": "AP Battery System,EC motor,Variable speed"},
    {"model": "BGA 100", "name": "BGA 100", "cat": "Blowers", "sub": "Battery Blowers", "power": "Battery", "segment": "Professional", "cc": None, "bar": None, "weight": 8.2, "msrp": 399.99, "cost": 195.00, "desc": "High-output professional battery blower.", "features": "AP Battery System,EC motor,Cruise control"},
    {"model": "BGA 200", "name": "BGA 200", "cat": "Blowers", "sub": "Battery Blowers", "power": "Battery", "segment": "Professional", "cc": None, "bar": None, "weight": 9.5, "msrp": 499.99, "cost": 245.00, "desc": "Maximum power battery blower for professional use.", "features": "AP Battery System,Brushless motor,Variable speed trigger"},
    
    # HEDGE TRIMMERS - Gas
    {"model": "HS 45", "name": "HS 45", "cat": "Hedge Trimmers", "sub": "Gas Hedge Trimmers", "power": "Gas", "segment": "Homeowner", "cc": 27.2, "bar": None, "weight": 10.8, "msrp": 299.99, "cost": 145.00, "desc": "Light and maneuverable gas hedge trimmer.", "features": "27.2cc engine,18-inch blade,Double-sided cutting"},
    {"model": "HS 56 C-E", "name": "HS 56 C-E", "cat": "Hedge Trimmers", "sub": "Gas Hedge Trimmers", "power": "Gas", "segment": "Professional", "cc": 27.2, "bar": None, "weight": 11.2, "msrp": 449.99, "cost": 220.00, "desc": "Professional hedge trimmer with Easy2Start.", "features": "Easy2Start,24-inch blade,Anti-vibration"},
    {"model": "HS 82 R", "name": "HS 82 R", "cat": "Hedge Trimmers", "sub": "Gas Hedge Trimmers", "power": "Gas", "segment": "Professional", "cc": 22.7, "bar": None, "weight": 11.6, "msrp": 549.99, "cost": 270.00, "desc": "Double-sided hedge trimmer for professional landscapers.", "features": "24-inch blade,Double-sided,Anti-vibration"},
    {"model": "HS 87 R", "name": "HS 87 R", "cat": "Hedge Trimmers", "sub": "Gas Hedge Trimmers", "power": "Gas", "segment": "Professional", "cc": 22.7, "bar": None, "weight": 12.1, "msrp": 649.99, "cost": 320.00, "desc": "Single-sided professional hedge trimmer for precision shaping.", "features": "30-inch blade,Single-sided,Anti-vibration,Low noise"},
    
    # HEDGE TRIMMERS - Battery
    {"model": "HSA 45", "name": "HSA 45", "cat": "Hedge Trimmers", "sub": "Battery Hedge Trimmers", "power": "Battery", "segment": "Homeowner", "cc": None, "bar": None, "weight": 5.5, "msrp": 149.99, "cost": 70.00, "desc": "Compact battery hedge trimmer for home gardening.", "features": "Integrated battery,20-inch blade,Lightweight"},
    {"model": "HSA 56", "name": "HSA 56", "cat": "Hedge Trimmers", "sub": "Battery Hedge Trimmers", "power": "Battery", "segment": "Homeowner", "cc": None, "bar": None, "weight": 6.4, "msrp": 199.99, "cost": 95.00, "desc": "Versatile battery hedge trimmer for the homeowner.", "features": "AK Battery System,18-inch blade,Double-sided"},
    {"model": "HSA 66", "name": "HSA 66", "cat": "Hedge Trimmers", "sub": "Battery Hedge Trimmers", "power": "Battery", "segment": "Professional", "cc": None, "bar": None, "weight": 8.4, "msrp": 349.99, "cost": 170.00, "desc": "Professional battery hedge trimmer with extended reach.", "features": "AP Battery System,20-inch blade,Double-sided"},
    {"model": "HSA 86", "name": "HSA 86", "cat": "Hedge Trimmers", "sub": "Battery Hedge Trimmers", "power": "Battery", "segment": "Professional", "cc": None, "bar": None, "weight": 9.5, "msrp": 449.99, "cost": 220.00, "desc": "High-performance professional battery hedge trimmer.", "features": "AP Battery System,24-inch blade,EC motor"},
    
    # PRESSURE WASHERS
    {"model": "RB 200", "name": "RB 200", "cat": "Pressure Washers", "sub": "Gas Pressure Washers", "power": "Gas", "segment": "Homeowner", "cc": 173.0, "bar": None, "weight": 48.0, "msrp": 349.99, "cost": 170.00, "desc": "Entry-level gas pressure washer for home cleaning tasks.", "features": "2500 PSI,2.3 GPM,Axial pump"},
    {"model": "RB 400", "name": "RB 400", "cat": "Pressure Washers", "sub": "Gas Pressure Washers", "power": "Gas", "segment": "Homeowner", "cc": 196.0, "bar": None, "weight": 55.0, "msrp": 449.99, "cost": 220.00, "desc": "Powerful pressure washer for tough home cleaning jobs.", "features": "2700 PSI,2.7 GPM,Triplex pump"},
    {"model": "RB 600", "name": "RB 600", "cat": "Pressure Washers", "sub": "Gas Pressure Washers", "power": "Gas", "segment": "Professional", "cc": 270.0, "bar": None, "weight": 82.0, "msrp": 799.99, "cost": 395.00, "desc": "Commercial-grade pressure washer for professional use.", "features": "3200 PSI,2.8 GPM,Honda engine"},
    {"model": "RB 800", "name": "RB 800", "cat": "Pressure Washers", "sub": "Gas Pressure Washers", "power": "Gas", "segment": "Professional", "cc": 389.0, "bar": None, "weight": 105.0, "msrp": 1199.99, "cost": 595.00, "desc": "Heavy-duty professional pressure washer.", "features": "4200 PSI,4.0 GPM,Honda engine,Direct drive"},
    
    # EDGERS
    {"model": "FC 56 C-E", "name": "FC 56 C-E", "cat": "Edgers", "sub": "Gas Edgers", "power": "Gas", "segment": "Homeowner", "cc": 27.2, "bar": None, "weight": 9.5, "msrp": 299.99, "cost": 145.00, "desc": "Compact gas edger for clean lawn edges.", "features": "Easy2Start,8-inch blade,Adjustable depth"},
    {"model": "FC 91", "name": "FC 91", "cat": "Edgers", "sub": "Gas Edgers", "power": "Gas", "segment": "Professional", "cc": 28.4, "bar": None, "weight": 11.2, "msrp": 449.99, "cost": 220.00, "desc": "Professional edger with 4-MIX engine.", "features": "4-MIX engine,8-inch blade,Low emissions"},
    {"model": "FCS 91", "name": "FCS 91", "cat": "Edgers", "sub": "Gas Edgers", "power": "Gas", "segment": "Professional", "cc": 28.4, "bar": None, "weight": 12.8, "msrp": 549.99, "cost": 270.00, "desc": "Straight shaft edger for professional landscaping.", "features": "4-MIX engine,Straight shaft,Multi-function handle"},
    {"model": "FCA 135", "name": "FCA 135", "cat": "Edgers", "sub": "Battery Edgers", "power": "Battery", "segment": "Professional", "cc": None, "bar": None, "weight": 9.2, "msrp": 399.99, "cost": 195.00, "desc": "Professional battery edger with all-day power.", "features": "AP Battery System,EC motor,8-inch blade"},
    
    # POLE PRUNERS
    {"model": "HT 56 C-E", "name": "HT 56 C-E", "cat": "Pole Pruners", "sub": "Gas Pole Pruners", "power": "Gas", "segment": "Homeowner", "cc": 27.2, "bar": None, "weight": 13.2, "msrp": 399.99, "cost": 195.00, "desc": "Extended reach pole pruner for homeowner tree care.", "features": "Easy2Start,12-inch bar,12-foot reach"},
    {"model": "HT 103", "name": "HT 103", "cat": "Pole Pruners", "sub": "Gas Pole Pruners", "power": "Gas", "segment": "Professional", "cc": 31.4, "bar": None, "weight": 14.8, "msrp": 549.99, "cost": 270.00, "desc": "Professional pole pruner with extended length.", "features": "4-MIX engine,12-inch bar,13-foot reach"},
    {"model": "HT 135", "name": "HT 135", "cat": "Pole Pruners", "sub": "Gas Pole Pruners", "power": "Gas", "segment": "Professional", "cc": 36.3, "bar": None, "weight": 16.1, "msrp": 699.99, "cost": 345.00, "desc": "Telescoping professional pole pruner.", "features": "4-MIX engine,14-inch bar,Telescoping shaft"},
    {"model": "HTA 66", "name": "HTA 66", "cat": "Pole Pruners", "sub": "Battery Pole Pruners", "power": "Battery", "segment": "Homeowner", "cc": None, "bar": None, "weight": 10.2, "msrp": 349.99, "cost": 170.00, "desc": "Battery pole pruner for quiet tree trimming.", "features": "AK Battery System,10-inch bar,Lightweight"},
    {"model": "HTA 86", "name": "HTA 86", "cat": "Pole Pruners", "sub": "Battery Pole Pruners", "power": "Battery", "segment": "Professional", "cc": None, "bar": None, "weight": 12.5, "msrp": 499.99, "cost": 245.00, "desc": "Professional battery pole pruner.", "features": "AP Battery System,12-inch bar,EC motor"},
    
    # WET/DRY VACS
    {"model": "SE 62", "name": "SE 62", "cat": "Wet Dry Vacuums", "sub": "Wet Dry Vacuums", "power": "Electric", "segment": "Homeowner", "cc": None, "bar": None, "weight": 12.5, "msrp": 199.99, "cost": 95.00, "desc": "Compact wet/dry vacuum for home workshop.", "features": "1100W motor,6.6 gallon,Blower function"},
    {"model": "SE 122", "name": "SE 122", "cat": "Wet Dry Vacuums", "sub": "Wet Dry Vacuums", "power": "Electric", "segment": "Professional", "cc": None, "bar": None, "weight": 19.8, "msrp": 399.99, "cost": 195.00, "desc": "Professional wet/dry vacuum with high suction power.", "features": "1500W motor,10 gallon,Auto filter clean"},
    
    # SPRAYERS
    {"model": "SG 31", "name": "SG 31", "cat": "Sprayers", "sub": "Manual Sprayers", "power": "Manual", "segment": "Homeowner", "cc": None, "bar": None, "weight": 7.5, "msrp": 99.99, "cost": 45.00, "desc": "Manual backpack sprayer for garden applications.", "features": "3.2 gallon,Manual pump,Adjustable nozzle"},
    {"model": "SG 51", "name": "SG 51", "cat": "Sprayers", "sub": "Manual Sprayers", "power": "Manual", "segment": "Homeowner", "cc": None, "bar": None, "weight": 9.2, "msrp": 149.99, "cost": 70.00, "desc": "Professional-grade manual backpack sprayer.", "features": "4.25 gallon,Viton seals,Multi-nozzle kit"},
    {"model": "SR 200", "name": "SR 200", "cat": "Sprayers", "sub": "Gas Sprayers", "power": "Gas", "segment": "Professional", "cc": 27.2, "bar": None, "weight": 18.5, "msrp": 549.99, "cost": 270.00, "desc": "Gas-powered backpack sprayer for large applications.", "features": "27.2cc engine,4.25 gallon,Mist blower"},
    {"model": "SR 450", "name": "SR 450", "cat": "Sprayers", "sub": "Gas Sprayers", "power": "Gas", "segment": "Professional", "cc": 63.3, "bar": None, "weight": 26.5, "msrp": 899.99, "cost": 445.00, "desc": "Commercial backpack sprayer for pest control professionals.", "features": "63.3cc engine,3.4 gallon,High velocity"},
]

# Calculate margin percentage
for p in PRODUCTS:
    p["margin_pct"] = round((p["msrp"] - p["cost"]) / p["msrp"] * 100, 1)

print(f"Total products: {len(PRODUCTS)}")
print(f"Categories: {set(p['cat'] for p in PRODUCTS)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Product Dimension Table

# COMMAND ----------

# Create product DataFrame
from pyspark.sql import Row
from datetime import date
import random

def generate_product_rows():
    rows = []
    for i, p in enumerate(PRODUCTS):
        # Generate launch date (older products launched earlier)
        base_year = 2018 if p["segment"] == "Professional" else 2019
        launch_date = date(
            base_year + random.randint(0, 4),
            random.randint(1, 12),
            random.randint(1, 28)
        )
        
        # Some products are discontinued (mostly older gas models)
        is_active = True
        discontinue_date = None
        if p["model"] in ["BG 50", "HS 45", "MS 170"] and random.random() < 0.3:
            is_active = False
            discontinue_date = date(2024, random.randint(1, 6), 15)
        
        rows.append(Row(
            product_id=f"P{str(i+1).zfill(4)}",
            model_number=p["model"],
            product_name=p["name"],
            category=p["cat"],
            subcategory=p["sub"],
            power_type=p["power"],
            user_segment=p["segment"],
            engine_displacement_cc=float(p["cc"]) if p["cc"] else None,
            bar_length_inches=float(p["bar"]) if p["bar"] else None,
            cutting_width_inches=None,
            weight_lbs=float(p["weight"]),
            msrp=float(p["msrp"]),
            cost=float(p["cost"]),
            margin_pct=float(p["margin_pct"]),
            price_effective_date=date(2024, 1, 1),
            description=p["desc"],
            features=p["features"],
            is_active=is_active,
            launch_date=launch_date,
            discontinue_date=discontinue_date,
            created_at=datetime.now(),
            updated_at=datetime.now()
        ))
    return rows

products_df = spark.createDataFrame(generate_product_rows())

# Write to silver
products_df.write.mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA_SILVER}.dim_products")

# Display sample
display(spark.table(f"{CATALOG}.{SCHEMA_SILVER}.dim_products"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Generate Sales History (24 Months)

# COMMAND ----------

import uuid
from datetime import date, timedelta

def generate_sales_data():
    """Generate 24 months of realistic sales data"""
    
    # Load products for reference
    products = spark.table(f"{CATALOG}.{SCHEMA_SILVER}.dim_products").collect()
    product_map = {p.product_id: p for p in products}
    
    sales_rows = []
    regions = ["East", "Central", "West", "South"]
    channels = ["Retail", "Pro Dealer", "Online"]
    
    # Regional weights (East and Central are larger markets)
    region_weights = {"East": 0.30, "Central": 0.28, "West": 0.25, "South": 0.17}
    
    # Channel weights (vary by segment)
    channel_weights_home = {"Retail": 0.60, "Pro Dealer": 0.15, "Online": 0.25}
    channel_weights_pro = {"Retail": 0.30, "Pro Dealer": 0.55, "Online": 0.15}
    
    # Seasonality factors (outdoor equipment peaks in spring/summer)
    month_seasonality = {
        1: 0.6, 2: 0.65, 3: 0.9, 4: 1.15, 5: 1.3, 6: 1.25,
        7: 1.1, 8: 1.0, 9: 0.95, 10: 0.85, 11: 0.75, 12: 0.7
    }
    
    # Category base daily sales (before seasonality)
    category_base_sales = {
        "Chainsaws": 8,
        "Trimmers": 12,
        "Blowers": 10,
        "Hedge Trimmers": 6,
        "Pressure Washers": 4,
        "Edgers": 3,
        "Pole Pruners": 2,
        "Wet Dry Vacuums": 2,
        "Sprayers": 2
    }
    
    # Power type growth factors (battery products growing faster)
    power_growth = {
        "Battery": 1.02,  # 2% monthly growth
        "Gas": 1.005,     # 0.5% monthly growth
        "Electric": 0.998, # slight decline
        "Manual": 1.0
    }
    
    # Generate daily sales
    current_date = START_DATE
    months_from_start = 0
    
    while current_date <= END_DATE:
        month = current_date.month
        seasonality = month_seasonality[month]
        
        # Track month changes for growth calculation
        if current_date.day == 1:
            months_from_start += 1
        
        for product in products:
            if not product.is_active:
                continue
            if product.launch_date and current_date < product.launch_date:
                continue
            if product.discontinue_date and current_date > product.discontinue_date:
                continue
            
            # Base daily sales for this category
            base_sales = category_base_sales.get(product.category, 3)
            
            # Adjust for user segment (pro products sell less but higher value)
            if product.user_segment == "Professional":
                base_sales *= 0.6
            
            # Apply seasonality
            adjusted_sales = base_sales * seasonality
            
            # Apply power type growth (compounded over months)
            growth_factor = power_growth.get(product.power_type, 1.0) ** months_from_start
            adjusted_sales *= growth_factor
            
            # Random daily variation
            daily_variation = random.uniform(0.5, 1.5)
            final_sales = int(adjusted_sales * daily_variation)
            
            if final_sales <= 0:
                continue
            
            # Distribute across regions and channels
            for region in regions:
                region_sales = int(final_sales * region_weights[region] * random.uniform(0.8, 1.2))
                if region_sales <= 0:
                    continue
                
                # Choose channel based on segment
                if product.user_segment == "Professional":
                    channel_w = channel_weights_pro
                else:
                    channel_w = channel_weights_home
                
                channel = random.choices(
                    list(channel_w.keys()),
                    weights=list(channel_w.values())
                )[0]
                
                # Calculate revenue (allow some price variation)
                price_variation = random.uniform(0.95, 1.0)  # Some discounting
                unit_price = float(product.msrp) * price_variation
                revenue = region_sales * unit_price
                cogs = region_sales * float(product.cost)
                margin = revenue - cogs
                
                sales_rows.append(Row(
                    sale_id=str(uuid.uuid4()),
                    sale_date=current_date,
                    product_id=product.product_id,
                    units_sold=region_sales,
                    unit_price=round(unit_price, 2),
                    revenue=round(revenue, 2),
                    cost_of_goods=round(cogs, 2),
                    gross_margin=round(margin, 2),
                    region=region,
                    channel=channel,
                    created_at=datetime.now()
                ))
        
        current_date += timedelta(days=1)
        
        # Progress indicator
        if current_date.day == 1:
            print(f"Generated sales through {current_date}")
    
    return sales_rows

print("Generating 24 months of sales data...")
sales_rows = generate_sales_data()
print(f"Generated {len(sales_rows)} sales records")

# Create DataFrame and write
sales_df = spark.createDataFrame(sales_rows)
sales_df.write.mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA_SILVER}.fact_sales")

display(spark.table(f"{CATALOG}.{SCHEMA_SILVER}.fact_sales").limit(10))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Generate Current Inventory Snapshot

# COMMAND ----------

def generate_inventory_snapshot():
    """Generate current inventory based on recent sales velocity"""
    
    today = date.today()
    
    # Load products and recent sales
    products = spark.table(f"{CATALOG}.{SCHEMA_SILVER}.dim_products").collect()
    
    # Calculate 30-day sales by product
    sales_30d = spark.sql(f"""
        SELECT 
            product_id,
            SUM(units_sold) as total_units,
            AVG(units_sold) as avg_daily_sales
        FROM {CATALOG}.{SCHEMA_SILVER}.fact_sales
        WHERE sale_date >= date_sub(current_date(), 30)
        GROUP BY product_id
    """).collect()
    
    sales_map = {s.product_id: s for s in sales_30d}
    
    inventory_rows = []
    
    for product in products:
        if not product.is_active:
            continue
        
        sales_data = sales_map.get(product.product_id)
        avg_daily_sales = sales_data.avg_daily_sales if sales_data else 5.0
        
        # Calculate inventory levels
        # Higher-selling products should have more inventory
        target_days_supply = 30 if product.user_segment == "Professional" else 21
        base_inventory = int(avg_daily_sales * target_days_supply)
        
        # Add randomness
        on_hand = int(base_inventory * random.uniform(0.5, 1.5))
        in_transit = int(base_inventory * random.uniform(0.1, 0.3))
        reserved = int(on_hand * random.uniform(0.05, 0.15))
        available = on_hand - reserved
        
        # Reorder point
        reorder_point = int(avg_daily_sales * 14)  # 2 weeks supply
        
        # Stock status
        is_low_stock = available < reorder_point
        is_out_of_stock = available <= 0
        
        # Days of supply
        days_of_supply = int(available / avg_daily_sales) if avg_daily_sales > 0 else 999
        
        inventory_rows.append(Row(
            snapshot_date=today,
            product_id=product.product_id,
            total_on_hand=on_hand,
            total_in_transit=in_transit,
            total_reserved=reserved,
            total_available=available,
            reorder_point=reorder_point,
            reorder_quantity=int(reorder_point * 2),
            is_low_stock=is_low_stock,
            is_out_of_stock=is_out_of_stock,
            avg_daily_sales=round(avg_daily_sales, 2),
            days_of_supply=days_of_supply,
            updated_at=datetime.now()
        ))
    
    return inventory_rows

print("Generating current inventory snapshot...")
inventory_rows = generate_inventory_snapshot()
inventory_df = spark.createDataFrame(inventory_rows)
inventory_df.write.mode("overwrite").saveAsTable(f"{CATALOG}.{SCHEMA_SILVER}.fact_inventory_current")

display(spark.table(f"{CATALOG}.{SCHEMA_SILVER}.fact_inventory_current"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Verify Data Generation

# COMMAND ----------

# Summary statistics
print("=" * 60)
print("DATA GENERATION SUMMARY")
print("=" * 60)

products_count = spark.table(f"{CATALOG}.{SCHEMA_SILVER}.dim_products").count()
print(f"\nProducts: {products_count}")

sales_count = spark.table(f"{CATALOG}.{SCHEMA_SILVER}.fact_sales").count()
print(f"Sales records: {sales_count:,}")

inventory_count = spark.table(f"{CATALOG}.{SCHEMA_SILVER}.fact_inventory_current").count()
print(f"Inventory records: {inventory_count}")

# Category breakdown
print("\nProducts by Category:")
display(spark.sql(f"""
    SELECT category, COUNT(*) as count, 
           SUM(CASE WHEN is_active THEN 1 ELSE 0 END) as active
    FROM {CATALOG}.{SCHEMA_SILVER}.dim_products
    GROUP BY category
    ORDER BY count DESC
"""))

# Sales summary
print("\nSales Summary (24 months):")
display(spark.sql(f"""
    SELECT 
        ROUND(SUM(revenue)/1000000, 2) as total_revenue_millions,
        SUM(units_sold) as total_units,
        COUNT(DISTINCT product_id) as products_sold,
        MIN(sale_date) as first_sale,
        MAX(sale_date) as last_sale
    FROM {CATALOG}.{SCHEMA_SILVER}.fact_sales
"""))

# Inventory health
print("\nInventory Health:")
display(spark.sql(f"""
    SELECT 
        COUNT(*) as total_products,
        SUM(CASE WHEN is_low_stock THEN 1 ELSE 0 END) as low_stock,
        SUM(CASE WHEN is_out_of_stock THEN 1 ELSE 0 END) as out_of_stock,
        ROUND(AVG(days_of_supply), 1) as avg_days_of_supply
    FROM {CATALOG}.{SCHEMA_SILVER}.fact_inventory_current
"""))

print("\n✅ Sample data generation complete!")
