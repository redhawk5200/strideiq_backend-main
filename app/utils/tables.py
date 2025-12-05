from typing import Any, Dict, List


def _detect_tabular_intent(question: str) -> bool:
    """
    Detect if the user's question is likely requesting tabular data.
    """
    tabular_keywords = [
        'specifications', 'specs', 'parameters', 'values', 'settings',
        'table', 'chart', 'list', 'comparison', 'dimensions', 'tolerances',
        'measurements', 'clearances', 'torque', 'pressure', 'temperature',
        'motor', 'shaft', 'bearing', 'coupling', 'alignment', 'runout',
        'configuration', 'setup', 'calibration', 'inspection',
        'limits', 'ranges', 'recommended', 'maximum', 'minimum'
    ]
    
    question_lower = question.lower()
    return any(keyword in question_lower for keyword in tabular_keywords)

def _extract_tables_from_agent_response(agent_response: str) -> List[Dict[str, Any]]:
    """
    Extract table data from agent response and format for rendering.
    """
    tables = []
    
    # Look for CSV-like content in the response
    lines = agent_response.split('\n')
    current_table = []
    table_started = False
    table_metadata = {}
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Detect table metadata (Source, Table info)
        if line.startswith('Source:'):
            if current_table and table_started:
                # Save previous table
                tables.append(_format_table_data(current_table, table_metadata))
                current_table = []
                table_started = False
            
            # Extract metadata
            table_metadata = _parse_table_metadata(line, lines[i:i+3])
            continue
        
        # Detect CSV content (contains commas and looks like data)
        if (',' in line and 
            not line.startswith('WARNING') and 
            not line.startswith('CAUTION') and
            len(line.split(',')) >= 2):
            
            if not table_started:
                table_started = True
            current_table.append(line)
        
        # End table detection
        elif table_started and (line == '' or not (',' in line)):
            if current_table:
                tables.append(_format_table_data(current_table, table_metadata))
                current_table = []
                table_started = False
                table_metadata = {}
    
    # Handle last table
    if current_table and table_started:
        tables.append(_format_table_data(current_table, table_metadata))
    
    return tables

def _parse_table_metadata(source_line: str, context_lines: List[str]) -> Dict[str, Any]:
    """Parse table metadata from source line and context."""
    metadata = {
        'source': '',
        'file': '',
        'page': '',
        'table_number': '',
        'title': ''
    }
    
    # Parse source line: "Source: IOM_3100 (File: IOM_3100.pdf, Page: 39)"
    if 'Source:' in source_line:
        parts = source_line.replace('Source:', '').strip()
        
        # Extract file and page info
        if '(File:' in parts and 'Page:' in parts:
            source_name = parts.split('(File:')[0].strip()
            file_info = parts.split('(File:')[1].split(',')[0].strip()
            page_info = parts.split('Page:')[1].replace(')', '').strip()
            
            metadata['source'] = source_name
            metadata['file'] = file_info
            metadata['page'] = page_info
    
    # Look for table information in next few lines
    for line in context_lines[1:3]:
        if 'Table' in line and ':' in line:
            table_info = line.split(':')[0].strip()
            metadata['table_number'] = table_info
            if len(line.split(':')) > 1:
                metadata['title'] = line.split(':')[1].strip()
            break
    
    return metadata

def _format_table_data(csv_lines: List[str], metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Format CSV lines into a structured table object."""
    if not csv_lines:
        return None
    
    # Clean and parse CSV data
    rows = []
    for line in csv_lines:
        # Handle quoted CSV properly
        import csv
        import io
        try:
            reader = csv.reader(io.StringIO(line))
            row = next(reader)
            # Clean empty cells and strip whitespace
            cleaned_row = [cell.strip() for cell in row if cell.strip()]
            if cleaned_row:  # Only add non-empty rows
                rows.append(cleaned_row)
        except:
            # Fallback to simple split
            row = [cell.strip() for cell in line.split(',') if cell.strip()]
            if row:
                rows.append(row)
    
    if not rows:
        return None
    
    # Determine if first row is header
    has_header = _detect_table_header(rows)
    
    table_data = {
        'type': 'table',
        'metadata': metadata,
        'has_header': has_header,
        'headers': rows[0] if has_header else [],
        'rows': rows[1:] if has_header else rows,
        'total_rows': len(rows) - (1 if has_header else 0),
        'total_columns': len(rows[0]) if rows else 0
    }
    
    return table_data

def _detect_table_header(rows: List[List[str]]) -> bool:
    """Detect if the first row is likely a header."""
    if len(rows) < 2:
        return False
    
    first_row = rows[0]
    second_row = rows[1]
    
    # Check if first row contains typical header words
    header_indicators = ['specification', 'parameter', 'value', 'type', 'size', 'limit', 'range']
    first_row_text = ' '.join(first_row).lower()
    
    if any(indicator in first_row_text for indicator in header_indicators):
        return True
    
    # Check if first row is all text and second row contains numbers
    first_has_numbers = any(char.isdigit() for cell in first_row for char in cell)
    second_has_numbers = any(char.isdigit() for cell in second_row for char in cell)
    
    return not first_has_numbers and second_has_numbers

def _convert_tables_to_markdown(tables: List[Dict[str, Any]]) -> str:
    """Convert table data to markdown format."""
    if not tables:
        return ""
    
    markdown_sections = []
    
    for table in tables:
        if not table or table.get('type') != 'table':
            continue
        
        # Add table metadata
        metadata = table.get('metadata', {})
        if metadata.get('source') or metadata.get('table_number'):
            title_parts = []
            if metadata.get('table_number'):
                title_parts.append(metadata['table_number'])
            if metadata.get('source'):
                title_parts.append(f"({metadata['source']})")
            if metadata.get('page'):
                title_parts.append(f"Page {metadata['page']}")
            
            if title_parts:
                markdown_sections.append(f"### {' '.join(title_parts)}\n")
        
        # Convert to markdown table
        headers = table.get('headers', [])
        rows = table.get('rows', [])
        
        if not rows:
            continue
        
        # Create markdown table
        if headers and table.get('has_header'):
            # Use provided headers
            header_row = "| " + " | ".join(headers) + " |"
            separator_row = "| " + " | ".join(['---'] * len(headers)) + " |"
            markdown_sections.append(header_row)
            markdown_sections.append(separator_row)
        else:
            # Create generic headers
            max_cols = max(len(row) for row in rows) if rows else 0
            headers = [f"Column {i+1}" for i in range(max_cols)]
            header_row = "| " + " | ".join(headers) + " |"
            separator_row = "| " + " | ".join(['---'] * len(headers)) + " |"
            markdown_sections.append(header_row)
            markdown_sections.append(separator_row)
        
        # Add data rows
        for row in rows:
            # Pad row to match header length
            padded_row = row + [''] * (len(headers) - len(row))
            row_text = "| " + " | ".join(str(cell) for cell in padded_row) + " |"
            markdown_sections.append(row_text)
        
        markdown_sections.append("")  # Empty line between tables
    
    return "\n".join(markdown_sections)