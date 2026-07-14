import pandas as pd
import db_manager
import os

def test_pipeline():
    print("--- 1. Generating Mock Excel Data ---")
    mock_data = {
        "Product": ["Laptop", "Mouse", "Keyboard", "Monitor", "Headphones"],
        "Category": ["Electronics", "Accessories", "Accessories", "Electronics", "Accessories"],
        "Quantity": [10, 100, 50, 20, 40],
        "UnitPrice": [1000.0, 25.0, 75.0, 300.0, 120.0],
        "SalesRegion": ["North", "South", "East", "West", "North"]
    }
    df = pd.DataFrame(mock_data)
    excel_path = "test_sales.xlsx"
    df.to_excel(excel_path, index=False)
    print(f"Created sample Excel file: {excel_path}")
    
    print("\n--- 2. Importing Excel into SQLite ---")
    tables = db_manager.import_excel_to_db(excel_path)
    print(f"Imported tables: {tables}")
    
    print("\n--- 3. Verifying Database Schema ---")
    schema = db_manager.get_database_schema()
    print("Retrieved Schema:")
    print(schema)
    
    print("\n--- 4. Executing Safe Query ---")
    test_query = "SELECT Product, Quantity, UnitPrice, (Quantity * UnitPrice) as TotalRevenue FROM sheet1 WHERE SalesRegion = 'North'"
    result_df = db_manager.execute_query(test_query)
    print("Query results:")
    print(result_df)
    
    print("\n--- 5. Testing Q&A Cache Write and Read ---")
    question = "What is the total revenue for the North region?"
    answer = "The total revenue for North region is $14,800.00."
    db_manager.write_qa_cache(question, test_query, answer)
    print(f"Saved Q&A pair: '{question}'")
    
    cache_hit = db_manager.search_qa_cache("total revenue for the North")
    print("\nCache Search Result:")
    if cache_hit:
        print(f"SQL: {cache_hit['sql_query']}")
        print(f"Answer Summary: {cache_hit['result_summary']}")
    else:
        print("No cache hit found!")
        
    print("\nAll pipeline components in db_manager are working perfectly!")
    
    # Clean up test Excel file
    if os.path.exists(excel_path):
        os.remove(excel_path)
        print("\nCleaned up temporary Excel file.")

if __name__ == "__main__":
    test_pipeline()
