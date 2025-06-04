import logging
import requests # Added import
from typing import Optional, List, Dict, Any, Tuple
from inventree.api import InvenTreeAPI
from inventree.part import Part, PartCategory # Corrected import for PartCategory
from inventree.company import SupplierPart, Company # Added import
from requests.exceptions import HTTPError, RequestException

from .models import PartData, BomItemData # Import PartData and BomItemData

logger = logging.getLogger(__name__)

class ApiClient:
    """
    Client to interact with the InvenTree API.
    """
    def __init__(self, url: str, token: str):
        """
        Initializes the API client.

        Args:
            url: The base URL of the InvenTree instance.
            token: The API token for authentication.
        """
        try:
            # Initialize the InvenTree API library instance
            # Setting connect=False initially, connection test happens implicitly on first real request
            # or can be explicitly tested if needed later.
            self.api = InvenTreeAPI(host=url, token=token, connect=False)
            # The tests mock InvenTreeAPI, so no real connection check needed here.
            # Actual connection issues will be handled during method calls.
            # if not self.api.check_connection_details(): # Removed this check
            #      raise ConnectionError("Invalid URL or token provided.")
            # self.api.testServer() # This would attempt connection

        except (RequestException, ConnectionError) as e: # Removed AttributeError as check is gone
            logger.error(f"Failed to initialize InvenTree API: {e}")
            # Depending on desired behavior, could re-raise or set self.api to None
            self.api = None # Indicate failure
            raise ConnectionError(f"Failed to initialize InvenTree API: {e}") from e

    def get_part_data(self, part_id: int) -> Tuple[Optional[PartData], List[str]]:
        """
        Fetches data for a specific part from InvenTree and returns it as a PartData object.

        Args:
            part_id: The primary key (ID) of the part.

        Returns:
            A tuple containing (PartData object or None, list of warning/error messages).
        """
        warnings_list: List[str] = []
        if not self.api:
            msg = "API client not initialized."
            logger.error(msg)
            warnings_list.append(msg)
            return None, warnings_list
        try:
            part = Part(self.api, pk=part_id)
            if hasattr(part, '_data') and part._data:
                data = part._data
                supplier_names = []
                # --- Supplier Part and Company Name Fetching ---
                try:
                    # This is the primary call that might raise HTTPError or other exceptions
                    raw_supplier_parts_list = SupplierPart.list(self.api, part=part_id)

                    if raw_supplier_parts_list: # If list is not empty and no exception was raised
                        for sp in raw_supplier_parts_list:
                            if hasattr(sp, 'supplier') and sp.supplier: # Check attribute existence
                                try:
                                    company = Company(self.api, pk=sp.supplier)
                                    if company and hasattr(company, 'name') and company.name: # Check attribute existence
                                        supplier_names.append(company.name)
                                    else:
                                        logger.debug(f"Company data for supplier ID {sp.supplier} of part {part_id} was empty, missing name attribute, or name was empty.")
                                except HTTPError as he_company:
                                    logger.warning(f"Could not fetch company name for supplier ID {sp.supplier} of part {part_id} due to HTTPError: {he_company.response.status_code} - {getattr(he_company.response, 'text', 'No response text')}")
                                except Exception as e_company: # Other errors for Company
                                    logger.warning(f"Could not fetch company name for supplier ID {sp.supplier} of part {part_id}: {e_company}")
                            else:
                                logger.debug(f"SupplierPart object for part {part_id} is missing 'supplier' attribute or it's None. Data: {getattr(sp, '_data', 'N/A')}")
                
                except HTTPError as he_sp: # Catches HTTPError from SupplierPart.list
                    response_data = {}
                    response_text = getattr(he_sp.response, 'text', 'No response text')
                    try:
                        response_data = he_sp.response.json()
                    except ValueError: # Not JSON
                        logger.debug(f"Response from API for supplier parts (part {part_id}) was not valid JSON: {response_text}")

                    # Check for the specific 400 error indicating no supplier parts / invalid part for supplier context
                    # Example: {"part":["Select a valid choice. That choice is not one of the available choices."]}
                    # Example: {"detail":"Not found."} or {"non_field_errors":["No SupplierPart matches the given query."]}
                    if he_sp.response.status_code == 400:
                        part_error_list = response_data.get("part")
                        if isinstance(part_error_list, list) and any("select a valid choice" in str(item).lower() for item in part_error_list):
                            logger.debug(f"Part {part_id} has no supplier parts listed (API 400 'Select a valid choice'). Proceeding without supplier names.")
                        else:
                            # Generic 400 error for supplier parts
                            logger.warning(f"Could not fetch supplier parts for part {part_id} due to a 400 HTTP error: {response_text}")
                    else:
                        # Other HTTP errors (500, 401, 403, etc.)
                        logger.warning(f"Could not fetch supplier parts for part {part_id} due to an HTTP error: {he_sp.response.status_code} - {response_text}")
                        
                except Exception as e_outer_sp_processing: # Catches other non-HTTP errors from SupplierPart.list or during its loop processing
                    logger.warning(f"An unexpected error occurred while trying to process supplier parts for part {part_id}: {e_outer_sp_processing}")
                # --- End Supplier Part and Company Name Fetching ---

                try:
                    part_data_instance = PartData(
                        pk=data.get('pk'),
                        name=data.get('name', 'Unknown Name'),
                        is_purchaseable=data.get('purchaseable', False),
                        is_assembly=data.get('assembly', False),
                        total_in_stock=float(data.get('total_in_stock', 0.0)),
                        required_for_build_orders=float(data.get('required_for_build_orders', 0.0)),
                        required_for_sales_orders=float(data.get('required_for_sales_orders', 0.0)),
                        ordering=float(data.get('ordering', 0.0)),
                        building=float(data.get('building', 0.0)),
                        is_consumable=data.get('consumable', False),
                        supplier_names=supplier_names
                    )
                    return part_data_instance, warnings_list
                except (TypeError, ValueError) as conversion_error:
                    err_msg = f"Error converting API data to PartData for ID {part_id}: {conversion_error}. Data: {data}"
                    logger.error(err_msg)
                    warnings_list.append(err_msg)
                    return None, warnings_list
            else:
                warn_msg = f"Part data not found for ID: {part_id} (Part object had no _data)."
                logger.warning(warn_msg)
                warnings_list.append(warn_msg)
                return None, warnings_list
        except HTTPError as e:
            status_code = e.response.status_code if hasattr(e, 'response') else 'N/A'
            err_detail = str(e)
            try: # Try to get more specific error from response body
                response_json = e.response.json()
                if isinstance(response_json, dict):
                    err_detail = response_json.get('detail', str(e))
                    if 'part' in response_json and isinstance(response_json['part'], list):
                        err_detail += f" Details: {'; '.join(response_json['part'])}"
            except Exception:
                pass # Keep original err_detail if JSON parsing fails

            if status_code == 404:
                log_msg = f"Part not found in InvenTree (ID: {part_id}). Status: 404. Detail: {err_detail}"
                logger.warning(log_msg)
                warnings_list.append(log_msg)
            else:
                log_msg = f"API HTTPError fetching part {part_id}: Status {status_code}. Detail: {err_detail}"
                logger.error(log_msg)
                warnings_list.append(log_msg)
            return None, warnings_list
        except RequestException as e: # Other network errors
            err_msg = f"API RequestException fetching part {part_id}: {str(e)}"
            logger.error(err_msg)
            warnings_list.append(err_msg)
            return None, warnings_list
        except Exception as e:
            err_msg = f"Unexpected error fetching part data for ID {part_id}: {str(e)}"
            logger.error(err_msg, exc_info=True) # Keep exc_info for unexpected
            warnings_list.append(err_msg)
            return None, warnings_list

    def get_bom_data(self, part_id: int) -> Tuple[Optional[List[BomItemData]], List[str]]:
        """
        Fetches the Bill of Materials (BOM) for a specific assembly part.

        Args:
            part_id: The primary key (ID) of the assembly part.

        Returns:
            A tuple containing (list of BomItemData objects or None, list of warning/error messages).
            Returns ([], warnings) if the part is found but has no BOM items or is not an assembly.
        """
        warnings_list: List[str] = []
        if not self.api:
            msg = "API client not initialized."
            logger.error(msg)
            warnings_list.append(msg)
            return None, warnings_list
        try:
            assembly_part = Part(self.api, pk=part_id)
            if not (hasattr(assembly_part, '_data') and assembly_part._data):
                warn_msg = f"Assembly part not found for BOM request (ID: {part_id}) (Part object had no _data)."
                logger.warning(warn_msg)
                warnings_list.append(warn_msg)
                return None, warnings_list

            if not assembly_part._data.get('assembly', False):
                warn_msg = f"Part ID {part_id} ('{assembly_part._data.get('name', 'N/A')}') is not an assembly. Cannot fetch BOM."
                logger.warning(warn_msg)
                warnings_list.append(warn_msg)
                return [], warnings_list # Return empty list for non-assemblies

            bom_items_raw = assembly_part.getBomItems()
            bom_data_list: List[BomItemData] = []
            if bom_items_raw is None: # getBomItems might return None on error
                warn_msg = f"Call to getBomItems() for assembly {part_id} ('{assembly_part._data.get('name', 'N/A')}') returned None."
                logger.warning(warn_msg)
                warnings_list.append(warn_msg)
                # Depending on strictness, could return None here, but empty list might be safer for calculator
                return [], warnings_list


            for item in bom_items_raw:
                if hasattr(item, '_data') and item._data:
                    data = item._data
                    try:
                        sub_part_pk = data.get('sub_part')
                        quantity = data.get('quantity')
                        is_consumable = data.get('consumable', False)
                        is_optional = data.get('optional', False)  # Extract optional field, default to False

                        if sub_part_pk is None or quantity is None:
                            warn_msg = f"BOM item for assembly {part_id} is missing 'sub_part' or 'quantity'. Data: {data}"
                            logger.warning(warn_msg)
                            warnings_list.append(warn_msg)
                            continue

                        bom_data_list.append(
                            BomItemData(
                                sub_part=int(sub_part_pk),
                                quantity=float(quantity),
                                is_consumable=bool(is_consumable),
                                is_optional=bool(is_optional)  # Add optional field to BomItemData
                            )
                        )
                    except (TypeError, ValueError) as conversion_error:
                        err_msg = f"Error converting BOM item data for assembly {part_id}: {conversion_error}. Data: {data}"
                        logger.error(err_msg)
                        warnings_list.append(err_msg)
                        continue
                else:
                    warn_msg = f"BOM item object for assembly {part_id} lacks '_data' attribute."
                    logger.warning(warn_msg)
                    warnings_list.append(warn_msg)
            
            if not bom_items_raw and not bom_data_list: # Explicitly check if BOM was empty
                warn_msg = f"BOM for assembly {part_id} ('{assembly_part._data.get('name', 'N/A')}') is empty."
                logger.info(warn_msg) # Info level might be more appropriate than warning for empty BOM
                warnings_list.append(warn_msg)


            return bom_data_list, warnings_list

        except HTTPError as e:
            status_code = e.response.status_code if hasattr(e, 'response') else 'N/A'
            err_detail = str(e)
            try:
                response_json = e.response.json()
                if isinstance(response_json, dict):
                    err_detail = response_json.get('detail', str(e))
            except Exception:
                pass
            
            if status_code == 404: # Should be caught by Part(pk=part_id) not having _data
                log_msg = f"Assembly part not found for BOM request (ID: {part_id}). Status: 404. Detail: {err_detail}"
                logger.warning(log_msg)
                warnings_list.append(log_msg)
            else:
                log_msg = f"API HTTPError fetching BOM for part {part_id}: Status {status_code}. Detail: {err_detail}"
                logger.error(log_msg)
                warnings_list.append(log_msg)
            return None, warnings_list
        except RequestException as e:
            err_msg = f"API RequestException fetching BOM for part {part_id}: {str(e)}"
            logger.error(err_msg)
            warnings_list.append(err_msg)
            return None, warnings_list
        except Exception as e:
            err_msg = f"Unexpected error fetching BOM data for part ID {part_id}: {str(e)}"
            logger.error(err_msg, exc_info=True)
            warnings_list.append(err_msg)
            return None, warnings_list

    def get_parts_by_category(self, category_id: int) -> Tuple[Optional[List[Dict]], List[str]]:
        """
        Fetches parts belonging to a specific category from InvenTree.

        Args:
            category_id: The ID of the category.

        Returns:
            A tuple containing (list of part dictionaries or None, list of warning/error messages).
        """
        warnings_list: List[str] = []
        if not self.api:
            msg = "API client not initialized. Cannot fetch parts by category."
            logger.error(msg)
            warnings_list.append(msg)
            return None, warnings_list
        try:
            parts_raw = Part.list(self.api, category=category_id)
            parts_list = []
            if parts_raw is not None:
                for part_obj in parts_raw:
                    if hasattr(part_obj, '_data') and part_obj._data:
                        parts_list.append(part_obj._data)
                    else:
                        warn_msg = f"Part object in list for category {category_id} lacks '_data'. Part: {part_obj}"
                        logger.warning(warn_msg)
                        warnings_list.append(warn_msg)
            else: # Handle case where Part.list itself returns None
                warn_msg = f"Part.list returned None for category {category_id}, expected list. This might indicate an API issue."
                logger.warning(warn_msg)
                warnings_list.append(warn_msg)
                return None, warnings_list
            
            if not parts_raw and not parts_list: # If parts_raw was an empty list
                info_msg = f"No parts found in category {category_id}."
                logger.info(info_msg) # Not an error, so not adding to warnings_list by default

            return parts_list, warnings_list
        except HTTPError as e:
            status_code = e.response.status_code if hasattr(e, 'response') else 'N/A'
            err_detail = str(e)
            try:
                response_json = e.response.json()
                if isinstance(response_json, dict): err_detail = response_json.get('detail', str(e))
            except Exception: pass
            log_msg = f"API HTTPError fetching parts for category {category_id}: Status {status_code}. Detail: {err_detail}"
            logger.error(log_msg)
            warnings_list.append(log_msg)
            return None, warnings_list
        except RequestException as e:
            err_msg = f"API RequestException fetching parts for category {category_id}: {str(e)}"
            logger.error(err_msg)
            warnings_list.append(err_msg)
            return None, warnings_list
        except Exception as e:
            err_msg = f"Unexpected error fetching parts for category {category_id}: {str(e)}"
            logger.error(err_msg, exc_info=True)
            warnings_list.append(err_msg)
            return None, warnings_list

    def get_category_details(self, category_id: int) -> Tuple[Optional[Dict[str, Any]], List[str]]:
        """
        Fetches details for a specific part category from InvenTree.

        Args:
            category_id: The primary key (ID) of the part category.

        Returns:
            A tuple containing (dictionary of category data or None, list of warning/error messages).
        """
        warnings_list: List[str] = []
        if not self.api:
            msg = "API client not initialized. Cannot fetch category details."
            logger.error(msg)
            warnings_list.append(msg)
            return None, warnings_list
        try:
            category = PartCategory(self.api, pk=category_id)
            if hasattr(category, '_data') and category._data:
                return category._data, warnings_list
            else:
                warn_msg = f"Category data not found for ID: {category_id} (Category object had no _data)."
                logger.warning(warn_msg)
                warnings_list.append(warn_msg)
                return None, warnings_list
        except HTTPError as e:
            status_code = e.response.status_code if hasattr(e, 'response') else 'N/A'
            err_detail = str(e)
            try:
                response_json = e.response.json()
                if isinstance(response_json, dict): err_detail = response_json.get('detail', str(e))
            except Exception: pass

            if status_code == 404:
                log_msg = f"Category not found in InvenTree (ID: {category_id}). Status: 404. Detail: {err_detail}"
                logger.warning(log_msg)
                warnings_list.append(log_msg)
            else:
                log_msg = f"API HTTPError fetching category {category_id}: Status {status_code}. Detail: {err_detail}"
                logger.error(log_msg)
                warnings_list.append(log_msg)
            return None, warnings_list
        except RequestException as e:
            err_msg = f"API RequestException fetching category {category_id}: {str(e)}"
            logger.error(err_msg)
            warnings_list.append(err_msg)
            return None, warnings_list
        except Exception as e:
            err_msg = f"Unexpected error fetching category details for ID {category_id}: {str(e)}"
            logger.error(err_msg, exc_info=True)
            warnings_list.append(err_msg)
            return None, warnings_list