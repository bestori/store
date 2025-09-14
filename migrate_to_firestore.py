#!/usr/bin/env python3
"""
Migrate Excel products to Firebase Firestore.

This script converts all products from Excel files to Firestore documents,
enabling instant app startup and real database queries.
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import json

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app import create_app
from app.services.excel_loader import ExcelLoader
from app.services.firebase_service import FirebaseService
from app.models.product import Product


class FirestoreProductMigrator:
    """Migrate products from Excel files to Firestore."""
    
    def __init__(self, app_config: Dict[str, Any]):
        """Initialize the migrator."""
        self.logger = logging.getLogger(__name__)
        self.excel_loader = ExcelLoader(app_config)
        self.firebase_service = FirebaseService(app_config)
        
        # Migration stats
        self.stats = {
            'total_products': 0,
            'migrated_products': 0,
            'failed_products': 0,
            'start_time': None,
            'end_time': None,
            'errors': []
        }
    
    def load_excel_data(self) -> Dict[str, Any]:
        """Load all data from Excel files."""
        self.logger.info("Loading data from Excel files...")
        data = self.excel_loader.load_data()
        self.stats['total_products'] = len(data.get('products', []))
        self.logger.info(f"Loaded {self.stats['total_products']} products from Excel")
        return data
    
    def product_to_firestore_doc(self, product: Product) -> Dict[str, Any]:
        """Convert Product object to Firestore document format."""
        doc = {
            # Primary identifiers
            'menora_id': product.menora_id,
            'supplier_code': product.supplier_code,
            
            # Product information  
            'descriptions': {
                'hebrew': product.descriptions.hebrew if product.descriptions else '',
                'english': product.descriptions.english if product.descriptions else ''
            },
            'category': product.category,
            'subcategory': product.subcategory,
            
            # Technical specifications
            'specifications': product.specifications.to_dict() if product.specifications else {},
            
            # Pricing information
            'pricing': product.pricing.to_dict() if product.pricing else None,
            
            # Search terms
            'search_terms': product.search_terms or {},
            
            # Availability
            'in_stock': product.in_stock,
            'lead_time': product.lead_time,
            
            # Additional data
            'tags': product.tags or [],
            'supplier_name': product.supplier_name,
            
            # Image data
            'image_url': product.image_url,
            'image_path': product.image_path, 
            'has_image': product.has_image,
            
            # Migration metadata
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc),
            'migrated_from': 'excel',
            'migration_version': '1.0'
        }
        
        return doc
    
    def migrate_product(self, product: Product, skip_existing: bool = False) -> bool:
        """Migrate a single product to Firestore."""
        try:
            # Get Firestore client
            if not self.firebase_service.is_available():
                raise Exception("Firebase service not available")
            
            db = self.firebase_service._db
            doc_ref = db.collection('products').document(product.menora_id)
            
            # Check if product already exists (to prevent duplicates)
            if skip_existing:
                existing_doc = doc_ref.get()
                if existing_doc.exists:
                    self.logger.debug(f"Product {product.menora_id} already exists, skipping")
                    return True
            
            # Convert to Firestore document
            doc_data = self.product_to_firestore_doc(product)
            
            # Add/Update to products collection
            doc_ref.set(doc_data)
            
            self.stats['migrated_products'] += 1
            
            if self.stats['migrated_products'] % 50 == 0:
                self.logger.info(f"Migrated {self.stats['migrated_products']}/{self.stats['total_products']} products")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to migrate product {product.menora_id}: {str(e)}")
            self.stats['failed_products'] += 1
            self.stats['errors'].append({
                'product_id': product.menora_id,
                'error': str(e)
            })
            return False
    
    def migrate_all_products(self, excel_data: Dict[str, Any], dry_run: bool = False, skip_existing: bool = False) -> bool:
        """Migrate all products to Firestore."""
        self.logger.info(f"Starting migration of {self.stats['total_products']} products...")
        self.stats['start_time'] = datetime.now(timezone.utc)
        
        products = excel_data.get('products', [])
        
        if dry_run:
            self.logger.info("DRY RUN MODE - No actual migration will occur")
            
        success_count = 0
        for i, product in enumerate(products, 1):
            if dry_run:
                # Just validate the conversion
                try:
                    doc_data = self.product_to_firestore_doc(product)
                    success_count += 1
                    if i % 100 == 0:
                        self.logger.info(f"Validated {i}/{self.stats['total_products']} products")
                except Exception as e:
                    self.logger.error(f"Validation failed for product {product.menora_id}: {str(e)}")
            else:
                # Actual migration
                if self.migrate_product(product, skip_existing=skip_existing):
                    success_count += 1
        
        self.stats['end_time'] = datetime.now(timezone.utc)
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        self.logger.info(f"Migration completed in {duration:.2f} seconds")
        self.logger.info(f"Success: {success_count}/{self.stats['total_products']} products")
        
        if self.stats['failed_products'] > 0:
            self.logger.warning(f"Failed: {self.stats['failed_products']} products")
            
        return self.stats['failed_products'] == 0
    
    def create_firestore_indexes(self) -> bool:
        """Create necessary Firestore indexes for search."""
        self.logger.info("Creating Firestore indexes...")
        
        # Note: Firestore indexes need to be created via the console or CLI
        # This is a placeholder for index creation logic
        
        indexes_needed = [
            {
                'collection': 'products',
                'fields': ['category', 'in_stock'],
                'description': 'Category and availability filter'
            },
            {
                'collection': 'products', 
                'fields': ['supplier_name', 'category'],
                'description': 'Supplier and category filter'
            },
            {
                'collection': 'products',
                'fields': ['has_image', 'category'], 
                'description': 'Image availability filter'
            }
        ]
        
        self.logger.info(f"Indexes needed: {len(indexes_needed)}")
        for idx in indexes_needed:
            self.logger.info(f"  - {idx['collection']}: {idx['fields']} ({idx['description']})")
            
        self.logger.warning("Note: Indexes must be created manually in Firebase Console")
        return True
    
    def backup_excel_data(self, excel_data: Dict[str, Any], backup_file: Optional[str] = None) -> bool:
        """Create a backup of Excel data as JSON."""
        if backup_file is None:
            backup_file = f"excel_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
        self.logger.info(f"Creating backup: {backup_file}")
        
        try:
            # Convert products to serializable format
            backup_data = {
                'products': [],
                'prices': excel_data.get('prices', {}),
                'backup_created': datetime.now(timezone.utc).isoformat(),
                'total_products': len(excel_data.get('products', []))
            }
            
            for product in excel_data.get('products', []):
                product_dict = self.product_to_firestore_doc(product)
                # Convert datetime to string for JSON serialization
                product_dict['created_at'] = product_dict['created_at'].isoformat()
                product_dict['updated_at'] = product_dict['updated_at'].isoformat()
                backup_data['products'].append(product_dict)
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
                
            self.logger.info(f"Backup created successfully: {backup_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create backup: {str(e)}")
            return False
    
    def print_migration_summary(self):
        """Print migration summary."""
        print("\n" + "="*60)
        print("MIGRATION SUMMARY")
        print("="*60)
        print(f"Total products:     {self.stats['total_products']}")
        print(f"Migrated products:  {self.stats['migrated_products']}")
        print(f"Failed products:    {self.stats['failed_products']}")
        
        if self.stats['start_time'] and self.stats['end_time']:
            duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
            print(f"Duration:          {duration:.2f} seconds")
            
        if self.stats['errors']:
            print(f"\nErrors ({len(self.stats['errors'])}):")
            for error in self.stats['errors'][:5]:  # Show first 5 errors
                print(f"  - {error['product_id']}: {error['error']}")
            if len(self.stats['errors']) > 5:
                print(f"  ... and {len(self.stats['errors']) - 5} more errors")
                
        print("="*60)


def main():
    """Main migration function."""
    parser = argparse.ArgumentParser(description='Migrate Excel products to Firestore')
    parser.add_argument('--dry-run', action='store_true', help='Validate without migrating')
    parser.add_argument('--backup', type=str, help='Create backup file (optional filename)')
    parser.add_argument('--no-backup', action='store_true', help='Skip backup creation')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose logging')
    parser.add_argument('--skip-existing', action='store_true', help='Skip products that already exist (no duplicates)')
    
    args = parser.parse_args()
    
    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[logging.StreamHandler()]
    )
    
    logger = logging.getLogger(__name__)
    
    try:
        # Create Flask app for configuration
        logger.info("Initializing Flask app...")
        app = create_app('development')  # Use development for local migration
        
        with app.app_context():
            # Initialize migrator
            migrator = FirestoreProductMigrator(app.config)
            
            # Check Firebase connection
            if not migrator.firebase_service.is_available():
                logger.error("Firebase service not available! Check credentials.")
                return 1
                
            logger.info("Firebase connection successful")
            
            # Load Excel data
            excel_data = migrator.load_excel_data()
            
            if not excel_data.get('products'):
                logger.error("No products found in Excel data!")
                return 1
            
            # Create backup (unless disabled)
            if not args.no_backup:
                backup_file = args.backup if args.backup else None
                if not migrator.backup_excel_data(excel_data, backup_file):
                    logger.warning("Backup creation failed, continuing anyway...")
            
            # Run migration
            success = migrator.migrate_all_products(excel_data, dry_run=args.dry_run, skip_existing=args.skip_existing)
            
            # Create indexes info
            migrator.create_firestore_indexes()
            
            # Print summary
            migrator.print_migration_summary()
            
            if success:
                logger.info("Migration completed successfully!")
                if not args.dry_run:
                    logger.info("🎉 Products are now in Firestore! Update your app to use ProductService.")
                return 0
            else:
                logger.error("Migration completed with errors!")
                return 1
                
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        return 1


if __name__ == '__main__':
    sys.exit(main())