# Inventree Order Calculator

A command-line tool and web interface to calculate the required components for building a specified number of top-level assemblies based on Bill of Materials (BOM) data fetched from an InvenTree instance. Features include automatic detection of optional parts from InvenTree BOM data, comprehensive quantity calculations, and support for both CLI and Streamlit web interfaces.

## Requirements

- Python 3.8+
- `uv` (Python package installer and virtual environment manager)
- InvenTree instance with API access
- InvenTree version supporting BOM optional fields (for Optional column feature)

## Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd inventree-order-calculator
    ```
2.  **Install dependencies using `uv`:**
    This command creates a virtual environment (if one doesn't exist) and installs the packages specified in [`pyproject.toml`](pyproject.toml:0) and [`uv.lock`](uv.lock:0).
    ```bash
    uv sync
    ```

## Configuration

The tool requires access to your InvenTree instance. Configure the following environment variables:

-   `INVENTREE_URL`: The base URL of your InvenTree instance (e.g., `http://inventree.example.com`).
-   `INVENTREE_API_TOKEN`: Your InvenTree API token. You can generate this in your InvenTree user settings.
-   `INVENTREE_INSTANCE_URL` (Optional): The base URL of your InvenTree instance, used for generating clickable links to parts in the output (e.g., `https://my.inventree.server`). If not provided, links will not be generated.

You can set these variables directly in your shell environment:

```bash
export INVENTREE_URL="http://inventree.example.com/api/"
export INVENTREE_API_TOKEN="your_api_token_here"
export INVENTREE_INSTANCE_URL="http://inventree.example.com"
```

Alternatively, you can create a `.env` file in the project's root directory:

```dotenv
# .env
INVENTREE_URL=http://inventree.example.com/api/
INVENTREE_API_TOKEN=your_api_token_here
INVENTREE_INSTANCE_URL=http://inventree.example.com
```

The tool will automatically load variables from the `.env` file if it exists.

> **Note:** An example configuration file [`.env.example`](.env.example:0) is provided. Copy this file to `.env` and replace the placeholder values with your actual InvenTree API URL, API token, and instance URL.

## Usage

Run the calculator using `uv run`. Provide the part number (IPN - Internal Part Number) and the desired quantity for each top-level assembly you want to calculate the requirements for.

The format is `PART_IPN:QUANTITY`.

**Example:**

To calculate the components needed to build 10 units of part `PART_ID_1` and 5 units of part `PART_ID_2`:

```bash
uv run python -m inventree_order_calculator PART_ID_1:10 PART_ID_2:5
```

The tool will output two Markdown-formatted tables:

1.  **Parts to Order:** Lists purchasable components where the `To Order` quantity (calculated as `Total Required - Available Stock`) is greater than 0. This calculation intentionally ignores any `On Order` quantity to reflect immediate needs against current physical stock.
2.  **Subassemblies to Build:** Lists subassemblies that need to be manufactured. An assembly appears here if its `To Build` quantity (calculated as `Total Required - (Available Stock + In Production)`) is greater than 0, OR if it has an `In Production` quantity greater than 0 (even if `Total Required` is met). This ensures visibility of ongoing production.

These tables provide a clear overview of what needs to be procured or manufactured to fulfill the specified top-level assembly builds.

### Optional Parts Column

Both output tables include an **Optional** column that indicates whether each part or assembly is marked as optional in the InvenTree BOM. This feature leverages InvenTree's native BOM optional field support:

- **✓ (Checkmark)**: Indicates the part is optional for the assembly
- **✗ (X mark)**: Indicates the part is required for the assembly

**Important:** Optional parts are still included in quantity calculations and ordering recommendations. The Optional column serves as an informational indicator to help you make informed decisions about which parts to actually order or build. You may choose to defer ordering optional components based on your specific requirements, budget constraints, or availability.

**InvenTree Integration:** The optional status is automatically extracted from your InvenTree BOM data. When you mark a BOM item as "optional" in InvenTree, this information is preserved and displayed in the calculator's output tables.

#### Table Column Layout

**Parts to Order Table:**
- Part ID | Optional | Part Name | Needed | Total In Stock | Required for Build Orders | Required for Sales Orders | Available | To Order | On Order | Belongs to

**Subassemblies to Build Table:**
- Part ID | Optional | Part Name | Needed | Total In Stock | Required for Build Orders | Required for Sales Orders | Available | In Production | To Build | Belongs to

The Optional column is positioned prominently after the Part ID to provide immediate visibility of the optional status for each item.

**Backward Compatibility:** If your InvenTree instance doesn't support the optional field or if BOM items don't have the optional field set, all parts will be marked as required (✗) by default. The calculator remains fully functional with older InvenTree versions.

#### Example Output

**CLI Output:**
```
┏━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━┓
┃ Part ID ┃ Optional  ┃ Part Name                      ┃ Needed  ┃ To Order        ┃
┡━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━┩
│ 12345   │ ✗         │ Main Processor                 │ 10.00   │ 5.00            │
│ 12346   │ ✓         │ Optional LED Indicator         │ 10.00   │ 10.00           │
│ 12347   │ ✗         │ Power Supply                   │ 10.00   │ 3.00            │
└─────────┴───────────┴────────────────────────────────┴─────────┴─────────────────┘
```

**Streamlit Output:**
The web interface displays the same information with enhanced formatting, clickable part links, and checkbox-style indicators for the Optional column.

### Filtering Consumables

Parts can be marked as "consumable" in InvenTree (e.g., solder, glue, cleaning supplies). By default, these parts are included in the calculation results.

**CLI:**
You can exclude consumable parts from the output tables using the `--hide-consumables` flag:
```bash
uv run python -m inventree_order_calculator PART_ID_1:10 --hide-consumables
```

**Streamlit UI:**
The Streamlit interface provides a toggle switch labeled "Consumables anzeigen" (Show Consumables). By default, it is on (consumables are shown). Toggling it off will filter consumable parts from the displayed tables.

### Filtering by Supplier (HAIP Solutions GmbH)

The tool allows filtering out parts supplied by "HAIP Solutions GmbH".

**CLI:**
Use the `--hide-haip-parts` flag to exclude parts from this supplier:
```bash
uv run python -m inventree_order_calculator PART_ID_1:10 --hide-haip-parts
```

**Streamlit UI:**
A toggle switch labeled "HAIP Solutions Teile ausblenden" (Hide HAIP Solutions Parts) is available. By default, it is off (parts are shown). Toggling it on will filter these parts from the displayed tables.

### Filtering Optional Parts

The tool allows you to hide optional parts from the output tables, which can be useful when you want to focus only on required components for your build.

**CLI:**
Use the `--hide-optional-parts` flag to exclude optional parts from the output:
```bash
uv run python -m inventree_order_calculator PART_ID_1:10 --hide-optional-parts
```

**Streamlit UI:**
A toggle switch labeled "Show Optional Parts" is available in the Display Options section. By default, it is on (optional parts are shown). Toggling it off will filter optional parts from both the "Parts to Order" and "Assemblies to Build" tables.

**Filtering Order:**
When multiple filters are applied, they are processed in the following order:
1. Consumables filtering (if `--hide-consumables` is used)
2. HAIP Solutions GmbH filtering (if `--hide-haip-parts` is used)
3. Optional parts filtering (if `--hide-optional-parts` is used)

This allows for fine-grained control over which parts appear in your output tables.

## Streamlit Web Interface

In addition to the command-line interface, the tool provides a user-friendly web interface built with Streamlit. To launch the web interface:

```bash
uv run streamlit run src/inventree_order_calculator/streamlit_app.py
```

The web interface provides:

- **Interactive Input:** Easy-to-use forms for entering part identifiers and quantities
- **Real-time Calculation:** Instant results as you modify inputs
- **Enhanced Tables:** Rich formatting with clickable links to InvenTree parts
- **Optional Column Display:** Clear checkbox indicators (☑/☐) showing which parts are optional
- **Filtering Controls:** Toggle switches for consumables, HAIP Solutions parts, and optional parts
- **Export Options:** Download results as CSV or Excel files

The Optional column in the Streamlit interface uses checkbox-style indicators for better visual clarity compared to the CLI's text symbols.
## Running with Docker Compose

To run the Inventree Order Calculator using Docker Compose, follow these steps:

1.  **Create a `.env` file:**
    Copy the [`.env.example`](.env.example:0) file to `.env` in the project root:
    ```bash
    cp .env.example .env
    ```
    Then, open the `.env` file and fill in your InvenTree instance URL, API token, and optionally the instance URL for links:
    ```dotenv
    # .env
    INVENTREE_URL=http://your-inventree-instance.com/api/
    INVENTREE_API_TOKEN=your_api_token_here
    INVENTREE_INSTANCE_URL=http://your-inventree-instance.com # Optional, for clickable links
    ```

2.  **Build and run the application (Detached Mode with Dynamic Port):**
    Use the following command from the project root directory to start the services in detached mode. Docker will assign a random available port on the host to the container's port 8501.
    ```bash
    docker-compose up --build -d
    ```
    This command will build the Docker image (if it doesn't exist or if changes are detected) and start the application container in the background. The `--build` flag ensures the image is rebuilt if the `Dockerfile` or project files change.

3.  **Find the Assigned Host Port:**
    After the containers are started, you can find out which host port was assigned to the `inventree-calculator` service's port 8501 using:
    ```bash
    docker-compose port inventree-calculator 8501
    ```
    The output will be in the format `0.0.0.0:XXXXX` or `::XXXXX`, where `XXXXX` is the dynamically assigned host port.

4.  **Access the application:**
    The Streamlit application will then be accessible in your web browser at `http://localhost:XXXXX` (replace `XXXXX` with the port number you found in the previous step).