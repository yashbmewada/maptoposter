import osmnx as ox
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import matplotlib.colors as mcolors
import numpy as np
from geopy.geocoders import Nominatim
from tqdm import tqdm
import time
import json
import os
from datetime import datetime
import argparse
from dataclasses import dataclass
from typing import Optional, Tuple

THEMES_DIR = "themes"
FONTS_DIR = "fonts"
POSTERS_DIR = "posters"

# ============================================================================
# Data Models
# ============================================================================

@dataclass
class AddressHighlight:
    """Represents a highlighted address on the map."""
    
    address: str                    # Full street address
    lat: float                      # Latitude
    lon: float                      # Longitude
    x: float                        # Map x coordinate
    y: float                        # Map y coordinate
    marker_style: str = 'circle'    # 'circle', 'pin', or 'star'
    fill_color: str = '#FF4444'     # Marker fill color
    outline_color: str = '#FFFFFF'  # Marker outline color
    annotation: Optional[str] = None  # Custom text

# ============================================================================
# Address Geocoding Module
# ============================================================================

class GeocodingError(Exception):
    """Raised when address cannot be geocoded."""
    
    def __init__(self, address: str, suggestion: str):
        self.address = address
        self.suggestion = suggestion
        super().__init__(
            f"Could not geocode address: '{address}'\n"
            f"Suggestion: {suggestion}"
        )

class AddressOutOfBoundsError(Exception):
    """Raised when address is outside map boundary."""
    
    def __init__(self, address: str, distance: float, required_distance: float):
        self.address = address
        self.distance = distance
        self.required_distance = required_distance
        super().__init__(
            f"Address '{address}' is {distance:.0f}m from map center.\n"
            f"Try increasing --distance to at least {required_distance:.0f}m"
        )

def geocode_address(address: str, city: str, country: str) -> tuple:
    """
    Geocode a street address to latitude/longitude coordinates.
    
    Args:
        address: Full street address (e.g., "300 E Pike St, Seattle, WA 98122")
        city: City name for context
        country: Country name for context
    
    Returns:
        Tuple of (latitude, longitude)
    
    Raises:
        GeocodingError: If address cannot be geocoded
        ConnectionError: If geocoding service is unavailable
    """
    geolocator = Nominatim(user_agent="city_map_poster")
    
    # Construct full query string for better accuracy
    full_query = f"{address}, {city}, {country}"
    
    # Implement exponential backoff for rate limiting
    max_retries = 4
    retry_delays = [1, 2, 4, 8]  # seconds
    
    for attempt in range(max_retries):
        try:
            # Add rate limiting delay
            if attempt > 0:
                print(f"Retrying geocoding (attempt {attempt + 1}/{max_retries})...")
            time.sleep(retry_delays[attempt] if attempt < len(retry_delays) else 8)
            
            location = geolocator.geocode(full_query, timeout=10)
            
            if location:
                print(f"✓ Geocoded address: {location.address}")
                print(f"✓ Coordinates: {location.latitude}, {location.longitude}")
                return (location.latitude, location.longitude)
            else:
                # No results found
                suggestion = (
                    "Try providing a more complete address with street number, "
                    "street name, city, state/province, and postal code."
                )
                raise GeocodingError(address, suggestion)
                
        except Exception as e:
            if "timed out" in str(e).lower():
                if attempt < max_retries - 1:
                    continue  # Retry
                else:
                    raise ConnectionError(
                        f"Geocoding service timed out after {max_retries} attempts. "
                        "Please check your internet connection and try again."
                    )
            elif isinstance(e, GeocodingError):
                raise  # Re-raise our custom error
            else:
                # Other errors
                suggestion = "Check the address format and try again."
                raise GeocodingError(address, suggestion)
    
    # Should not reach here, but just in case
    raise GeocodingError(address, "Unable to geocode address after multiple attempts.")

def calculate_distance_between_points(point1: tuple, point2: tuple) -> float:
    """
    Calculate great circle distance between two lat/lon points in meters.
    Uses Haversine formula.
    
    Args:
        point1: (lat, lon) of first point
        point2: (lat, lon) of second point
    
    Returns:
        Distance in meters
    """
    from math import radians, sin, cos, sqrt, atan2
    
    lat1, lon1 = point1
    lat2, lon2 = point2
    
    # Earth's radius in meters
    R = 6371000
    
    # Convert to radians
    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lon = radians(lon2 - lon1)
    
    # Haversine formula
    a = sin(delta_lat / 2) ** 2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = R * c
    
    return distance

def validate_coordinates_in_bounds(
    address_coords: tuple,
    center_coords: tuple,
    distance: int
) -> bool:
    """
    Check if address coordinates fall within the map boundary.
    
    Args:
        address_coords: (lat, lon) of the address
        center_coords: (lat, lon) of the map center
        distance: Map radius in meters
    
    Returns:
        True if address is within bounds, False otherwise
    """
    actual_distance = calculate_distance_between_points(address_coords, center_coords)
    return actual_distance <= distance

# ============================================================================
# Coordinate Transformation Module
# ============================================================================

def transform_latlon_to_map_coords(lat: float, lon: float, G) -> tuple:
    """
    Transform latitude/longitude to map x/y coordinates.
    
    Args:
        lat: Latitude of the address
        lon: Longitude of the address
        G: OSMnx graph with CRS projection information
    
    Returns:
        Tuple of (x, y) in map coordinate system
    """
    from pyproj import Transformer
    
    # Get the graph's CRS (Coordinate Reference System)
    # OSMnx graphs typically use UTM projection
    graph_crs = G.graph.get('crs', 'EPSG:4326')
    
    # Create transformer from WGS84 (EPSG:4326) to graph's CRS
    # WGS84 is the standard lat/lon coordinate system
    transformer = Transformer.from_crs('EPSG:4326', graph_crs, always_xy=True)
    
    # Transform coordinates
    # Note: pyproj expects (lon, lat) order when always_xy=True
    x, y = transformer.transform(lon, lat)
    
    return (x, y)

# ============================================================================
# Marker Color Selection Module
# ============================================================================

def calculate_luminance(hex_color: str) -> float:
    """
    Calculate relative luminance using WCAG formula.
    
    Args:
        hex_color: Hex color string (e.g., "#FF0000" or "FF0000")
    
    Returns:
        Luminance value (0.0 to 1.0)
    """
    # Remove '#' if present
    hex_color = hex_color.lstrip('#')
    
    # Convert hex to RGB (0-255)
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    
    # Convert to 0-1 range
    r = r / 255.0
    g = g / 255.0
    b = b / 255.0
    
    # Apply gamma correction (WCAG formula)
    def gamma_correct(channel):
        if channel <= 0.03928:
            return channel / 12.92
        else:
            return ((channel + 0.055) / 1.055) ** 2.4
    
    r = gamma_correct(r)
    g = gamma_correct(g)
    b = gamma_correct(b)
    
    # Calculate relative luminance
    luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
    
    return luminance

def calculate_contrast_ratio(hex_color1: str, hex_color2: str) -> float:
    """
    Calculate WCAG contrast ratio between two colors.
    
    Args:
        hex_color1: First hex color string
        hex_color2: Second hex color string
    
    Returns:
        Contrast ratio value (1.0 to 21.0)
    """
    lum1 = calculate_luminance(hex_color1)
    lum2 = calculate_luminance(hex_color2)
    
    # Ensure lighter color is in numerator
    lighter = max(lum1, lum2)
    darker = min(lum1, lum2)
    
    # Calculate contrast ratio
    contrast_ratio = (lighter + 0.05) / (darker + 0.05)
    
    return contrast_ratio

def get_marker_color(theme: dict) -> tuple:
    """
    Determine marker colors based on theme.
    
    Args:
        theme: Theme dictionary with color definitions
    
    Returns:
        Tuple of (fill_color, outline_color)
    """
    # Check if theme explicitly defines marker colors
    if 'marker_fill' in theme:
        fill_color = theme['marker_fill']
        outline_color = theme.get('marker_outline', '#FFFFFF')
        return (fill_color, outline_color)
    
    # Calculate contrasting colors based on background
    bg_color = theme.get('bg', '#FFFFFF')
    bg_luminance = calculate_luminance(bg_color)
    
    # Determine if background is light or dark
    if bg_luminance > 0.5:
        # Light background - use darker marker colors
        fill_color = '#FF4444'  # Red
        outline_color = '#FFFFFF'  # White
    else:
        # Dark background - use lighter marker colors
        fill_color = '#FF6666'  # Lighter red
        outline_color = '#000000'  # Black
    
    # Verify contrast ratio meets minimum 4.5:1
    contrast_fill = calculate_contrast_ratio(fill_color, bg_color)
    contrast_outline = calculate_contrast_ratio(outline_color, bg_color)
    
    # If contrast is insufficient, adjust colors
    if contrast_fill < 4.5:
        # Try alternative colors
        if bg_luminance > 0.5:
            fill_color = '#CC0000'  # Darker red
        else:
            fill_color = '#FF8888'  # Even lighter red
    
    if contrast_outline < 4.5:
        # Adjust outline color
        if bg_luminance > 0.5:
            outline_color = '#000000'  # Black
        else:
            outline_color = '#FFFFFF'  # White
    
    return (fill_color, outline_color)

# ============================================================================
# Marker Rendering Module
# ============================================================================

def render_circle_marker(ax, x, y, fill_color, outline_color, size):
    """
    Render a circular marker with outer ring.
    
    Args:
        ax: Matplotlib axes object
        x: X coordinate in map space
        y: Y coordinate in map space
        fill_color: Interior color of marker
        outline_color: Border color of marker
        size: Base marker size in points
    """
    # Draw outer ring at 1.5x size with outline color (50% opacity)
    ax.scatter(x, y, s=size * 1.5, c=outline_color, alpha=0.5, zorder=15, edgecolors='none')
    
    # Draw inner circle at 1.0x size with fill color
    ax.scatter(x, y, s=size, c=fill_color, alpha=1.0, zorder=15, edgecolors='none')
    
    # Draw center dot at 0.3x size with outline color
    ax.scatter(x, y, s=size * 0.3, c=outline_color, alpha=1.0, zorder=15, edgecolors='none')

def render_pin_marker(ax, x, y, fill_color, outline_color, size):
    """
    Render a map pin style marker.
    
    Args:
        ax: Matplotlib axes object
        x: X coordinate in map space
        y: Y coordinate in map space
        fill_color: Interior color of marker
        outline_color: Border color of marker
        size: Base marker size in points
    """
    from matplotlib.path import Path
    import matplotlib.patches as patches
    
    # Calculate pin dimensions based on size
    # Size is in points^2 for scatter, so we need to scale appropriately
    scale = (size / 200) ** 0.5  # Normalize to base size of 200
    
    # Pin dimensions (teardrop shape)
    circle_radius = 15 * scale
    tip_length = 25 * scale
    
    # Create teardrop path
    # Circle at top, pointed tip at bottom
    theta = np.linspace(0, 2 * np.pi, 50)
    circle_x = x + circle_radius * np.cos(theta)
    circle_y = y + tip_length + circle_radius * np.sin(theta)
    
    # Create vertices for the teardrop
    # Start with circle, then add tip point
    vertices = list(zip(circle_x, circle_y))
    vertices.append((x, y))  # Tip point at exact coordinates
    
    # Create path
    codes = [Path.MOVETO] + [Path.LINETO] * (len(vertices) - 2) + [Path.CLOSEPOLY]
    path = Path(vertices, codes)
    
    # Draw outline
    patch_outline = patches.PathPatch(path, facecolor=outline_color, edgecolor=outline_color, 
                                      linewidth=2, alpha=0.8, zorder=15)
    ax.add_patch(patch_outline)
    
    # Draw fill (slightly smaller)
    patch_fill = patches.PathPatch(path, facecolor=fill_color, edgecolor='none', 
                                   alpha=1.0, zorder=15)
    ax.add_patch(patch_fill)

def render_star_marker(ax, x, y, fill_color, outline_color, size):
    """
    Render a star-shaped marker.
    
    Args:
        ax: Matplotlib axes object
        x: X coordinate in map space
        y: Y coordinate in map space
        fill_color: Interior color of marker
        outline_color: Border color of marker
        size: Base marker size in points
    """
    # Layer large outline star with smaller fill star
    # Outer star (outline) at 1.5x size
    ax.scatter(x, y, s=size * 1.5, marker='*', c=outline_color, alpha=0.8, zorder=15, edgecolors='none')
    
    # Inner star (fill) at 1.0x size
    ax.scatter(x, y, s=size, marker='*', c=fill_color, alpha=1.0, zorder=15, edgecolors='none')

def render_heart_marker(ax, x, y, fill_color, outline_color, size):
    """
    Render a heart-shaped marker (currently hexagon as placeholder).
    
    Args:
        ax: Matplotlib axes object
        x: X coordinate in map space
        y: Y coordinate in map space
        fill_color: Interior color of marker
        outline_color: Border color of marker
        size: Base marker size in points
    """
    # Using hexagon marker as placeholder for heart
    # Outer hexagon (outline) at 1.5x size
    ax.scatter(x, y, s=size * 1.5, marker='h', c=outline_color, alpha=0.8, zorder=15, edgecolors='none')
    
    # Inner hexagon (fill) at 1.0x size
    ax.scatter(x, y, s=size, marker='h', c=fill_color, alpha=1.0, zorder=15, edgecolors='none')

def render_address_marker(ax, x, y, style='circle', fill_color='#FF4444', 
                          outline_color='#FFFFFF', size=200):
    """
    Render a marker at the specified map coordinates.
    
    Args:
        ax: Matplotlib axes object
        x: X coordinate in map space
        y: Y coordinate in map space
        style: Marker style ('circle', 'pin', 'star', 'heart')
        fill_color: Interior color of marker
        outline_color: Border color of marker
        size: Marker size in points
    """
    # Dispatch to appropriate marker function based on style
    if style == 'circle':
        render_circle_marker(ax, x, y, fill_color, outline_color, size)
    elif style == 'pin':
        render_pin_marker(ax, x, y, fill_color, outline_color, size)
    elif style == 'star':
        render_star_marker(ax, x, y, fill_color, outline_color, size)
    elif style == 'heart':
        render_heart_marker(ax, x, y, fill_color, outline_color, size)
    else:
        # Invalid marker style - fallback to circle with warning
        print(f"⚠ Warning: Invalid marker style '{style}'. Using 'circle' instead.")
        render_circle_marker(ax, x, y, fill_color, outline_color, size)

def load_fonts():
    """
    Load Roboto fonts from the fonts directory.
    Returns dict with font paths for different weights.
    """
    fonts = {
        'bold': os.path.join(FONTS_DIR, 'Roboto-Bold.ttf'),
        'regular': os.path.join(FONTS_DIR, 'Roboto-Regular.ttf'),
        'light': os.path.join(FONTS_DIR, 'Roboto-Light.ttf')
    }
    
    # Verify fonts exist
    for weight, path in fonts.items():
        if not os.path.exists(path):
            print(f"⚠ Font not found: {path}")
            return None
    
    return fonts

FONTS = load_fonts()

def generate_output_filename(city, theme_name, highlighted=False):
    """
    Generate unique output filename with city, theme, and datetime.
    
    Args:
        city: City name
        theme_name: Theme name
        highlighted: If True, include "highlighted" in filename
    
    Returns:
        Full path to output file
    """
    if not os.path.exists(POSTERS_DIR):
        os.makedirs(POSTERS_DIR)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    city_slug = city.lower().replace(' ', '_')
    
    # Sanitize city_slug to be filesystem-safe
    import re
    city_slug = re.sub(r'[^a-z0-9_-]', '', city_slug)
    
    if highlighted:
        filename = f"{city_slug}_{theme_name}_highlighted_{timestamp}.png"
    else:
        filename = f"{city_slug}_{theme_name}_{timestamp}.png"
    
    return os.path.join(POSTERS_DIR, filename)

def get_available_themes():
    """
    Scans the themes directory and returns a list of available theme names.
    """
    if not os.path.exists(THEMES_DIR):
        os.makedirs(THEMES_DIR)
        return []
    
    themes = []
    for file in sorted(os.listdir(THEMES_DIR)):
        if file.endswith('.json'):
            theme_name = file[:-5]  # Remove .json extension
            themes.append(theme_name)
    return themes

def load_theme(theme_name="feature_based"):
    """
    Load theme from JSON file in themes directory.
    """
    theme_file = os.path.join(THEMES_DIR, f"{theme_name}.json")
    
    if not os.path.exists(theme_file):
        print(f"⚠ Theme file '{theme_file}' not found. Using default feature_based theme.")
        # Fallback to embedded default theme
        return {
            "name": "Feature-Based Shading",
            "bg": "#FFFFFF",
            "text": "#000000",
            "gradient_color": "#FFFFFF",
            "water": "#C0C0C0",
            "parks": "#F0F0F0",
            "road_motorway": "#0A0A0A",
            "road_primary": "#1A1A1A",
            "road_secondary": "#2A2A2A",
            "road_tertiary": "#3A3A3A",
            "road_residential": "#4A4A4A",
            "road_default": "#3A3A3A"
        }
    
    with open(theme_file, 'r') as f:
        theme = json.load(f)
        print(f"✓ Loaded theme: {theme.get('name', theme_name)}")
        if 'description' in theme:
            print(f"  {theme['description']}")
        return theme

# Load theme (can be changed via command line or input)
THEME = None  # Will be loaded later

def create_gradient_fade(ax, color, location='bottom', zorder=10):
    """
    Creates a fade effect at the top or bottom of the map.
    """
    vals = np.linspace(0, 1, 256).reshape(-1, 1)
    gradient = np.hstack((vals, vals))
    
    rgb = mcolors.to_rgb(color)
    my_colors = np.zeros((256, 4))
    my_colors[:, 0] = rgb[0]
    my_colors[:, 1] = rgb[1]
    my_colors[:, 2] = rgb[2]
    
    if location == 'bottom':
        my_colors[:, 3] = np.linspace(1, 0, 256)
        extent_y_start = 0
        extent_y_end = 0.25
    else:
        my_colors[:, 3] = np.linspace(0, 1, 256)
        extent_y_start = 0.75
        extent_y_end = 1.0

    custom_cmap = mcolors.ListedColormap(my_colors)
    
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    y_range = ylim[1] - ylim[0]
    
    y_bottom = ylim[0] + y_range * extent_y_start
    y_top = ylim[0] + y_range * extent_y_end
    
    ax.imshow(gradient, extent=[xlim[0], xlim[1], y_bottom, y_top], 
              aspect='auto', cmap=custom_cmap, zorder=zorder, origin='lower')

def get_edge_colors_by_type(G):
    """
    Assigns colors to edges based on road type hierarchy.
    Returns a list of colors corresponding to each edge in the graph.
    """
    edge_colors = []
    
    for u, v, data in G.edges(data=True):
        # Get the highway type (can be a list or string)
        highway = data.get('highway', 'unclassified')
        
        # Handle list of highway types (take the first one)
        if isinstance(highway, list):
            highway = highway[0] if highway else 'unclassified'
        
        # Assign color based on road type
        if highway in ['motorway', 'motorway_link']:
            color = THEME['road_motorway']
        elif highway in ['trunk', 'trunk_link', 'primary', 'primary_link']:
            color = THEME['road_primary']
        elif highway in ['secondary', 'secondary_link']:
            color = THEME['road_secondary']
        elif highway in ['tertiary', 'tertiary_link']:
            color = THEME['road_tertiary']
        elif highway in ['residential', 'living_street', 'unclassified']:
            color = THEME['road_residential']
        else:
            color = THEME['road_default']
        
        edge_colors.append(color)
    
    return edge_colors

def get_edge_widths_by_type(G):
    """
    Assigns line widths to edges based on road type.
    Major roads get thicker lines.
    """
    edge_widths = []
    
    for u, v, data in G.edges(data=True):
        highway = data.get('highway', 'unclassified')
        
        if isinstance(highway, list):
            highway = highway[0] if highway else 'unclassified'
        
        # Assign width based on road importance
        if highway in ['motorway', 'motorway_link']:
            width = 1.2
        elif highway in ['trunk', 'trunk_link', 'primary', 'primary_link']:
            width = 1.0
        elif highway in ['secondary', 'secondary_link']:
            width = 0.8
        elif highway in ['tertiary', 'tertiary_link']:
            width = 0.6
        else:
            width = 0.4
        
        edge_widths.append(width)
    
    return edge_widths

def get_coordinates(city, country):
    """
    Fetches coordinates for a given city and country using geopy.
    Includes rate limiting to be respectful to the geocoding service.
    """
    print("Looking up coordinates...")
    geolocator = Nominatim(user_agent="city_map_poster")
    
    # Add a small delay to respect Nominatim's usage policy
    time.sleep(1)
    
    location = geolocator.geocode(f"{city}, {country}")
    
    if location:
        print(f"✓ Found: {location.address}")
        print(f"✓ Coordinates: {location.latitude}, {location.longitude}")
        return (location.latitude, location.longitude)
    else:
        raise ValueError(f"Could not find coordinates for {city}, {country}")

def create_poster(city, country, point, dist, output_file, annotation=None, address_highlight=None, date_text=None):
    print(f"\nGenerating map for {city}, {country}...")
    
    # Progress bar for data fetching
    with tqdm(total=3, desc="Fetching map data", unit="step", bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}') as pbar:
        # 1. Fetch Street Network
        pbar.set_description("Downloading street network")
        G = ox.graph_from_point(point, dist=dist, dist_type='bbox', network_type='all')
        pbar.update(1)
        time.sleep(0.5)  # Rate limit between requests
        
        # 2. Fetch Water Features
        pbar.set_description("Downloading water features")
        try:
            water = ox.features_from_point(point, tags={'natural': 'water', 'waterway': 'riverbank'}, dist=dist)
        except:
            water = None
        pbar.update(1)
        time.sleep(0.3)
        
        # 3. Fetch Parks
        pbar.set_description("Downloading parks/green spaces")
        try:
            parks = ox.features_from_point(point, tags={'leisure': 'park', 'landuse': 'grass'}, dist=dist)
        except:
            parks = None
        pbar.update(1)
    
    print("✓ All data downloaded successfully!")
    
    # 2. Setup Plot
    print("Rendering map...")
    fig, ax = plt.subplots(figsize=(12, 16), facecolor=THEME['bg'])
    ax.set_facecolor(THEME['bg'])
    ax.set_position([0, 0, 1, 1])
    
    # 3. Plot Layers
    # Layer 1: Polygons
    if water is not None and not water.empty:
        water.plot(ax=ax, facecolor=THEME['water'], edgecolor='none', zorder=1)
    if parks is not None and not parks.empty:
        parks.plot(ax=ax, facecolor=THEME['parks'], edgecolor='none', zorder=2)
    
    # Layer 2: Roads with hierarchy coloring
    print("Applying road hierarchy colors...")
    edge_colors = get_edge_colors_by_type(G)
    edge_widths = get_edge_widths_by_type(G)
    
    ox.plot_graph(
        G, ax=ax, bgcolor=THEME['bg'],
        node_size=0,
        edge_color=edge_colors,
        edge_linewidth=edge_widths,
        show=False, close=False
    )
    
    # Layer 2.5: Address Marker (after roads, before gradients)
    if address_highlight is not None:
        print("Rendering address marker...")
        # Transform lat/lon to map coordinates
        x, y = transform_latlon_to_map_coords(address_highlight.lat, address_highlight.lon, G)
        
        # Calculate marker size based on map distance
        if dist < 8000:
            marker_size = 300
        elif dist < 15000:
            marker_size = 200
        else:
            marker_size = 150
        
        # Render the marker
        render_address_marker(
            ax, x, y,
            style=address_highlight.marker_style,
            fill_color=address_highlight.fill_color,
            outline_color=address_highlight.outline_color,
            size=marker_size
        )
        print(f"✓ Address marker rendered at ({x:.2f}, {y:.2f})")
    
    # Layer 3: Gradients (Top and Bottom)
    create_gradient_fade(ax, THEME['gradient_color'], location='bottom', zorder=10)
    create_gradient_fade(ax, THEME['gradient_color'], location='top', zorder=10)
    
    # 4. Typography using Roboto font
    # When address is highlighted, make annotation prominent and city smaller
    if address_highlight is not None:
        # Romantic/gift mode: aesthetic, clean, romantic typography
        if FONTS:
            # Use Roboto but with better styling for romantic aesthetic
            font_annotation = FontProperties(fname=FONTS['light'], size=44)     # Light but large - elegant
            font_date = FontProperties(fname=FONTS['regular'], size=20)         # Regular - clear
            font_city = FontProperties(fname=FONTS['light'], size=13)           # Light - subtle
            font_coords = FontProperties(fname=FONTS['light'], size=9)          # Light - minimal
        else:
            # Fallback to elegant serif fonts
            font_annotation = FontProperties(family='serif', weight='light', size=44)
            font_date = FontProperties(family='serif', weight='normal', size=20)
            font_city = FontProperties(family='serif', weight='light', size=13)
            font_coords = FontProperties(family='serif', weight='light', size=9)
    else:
        # Normal mode: city is the main text
        if FONTS:
            font_main = FontProperties(fname=FONTS['bold'], size=60)
            font_top = FontProperties(fname=FONTS['bold'], size=40)
            font_sub = FontProperties(fname=FONTS['light'], size=22)
            font_coords = FontProperties(fname=FONTS['regular'], size=14)
        else:
            font_main = FontProperties(family='monospace', weight='bold', size=60)
            font_top = FontProperties(family='monospace', weight='bold', size=40)
            font_sub = FontProperties(family='monospace', weight='normal', size=22)
            font_coords = FontProperties(family='monospace', size=14)
    
    # Extract annotation from address_highlight if provided, otherwise use annotation parameter
    annotation_text = None
    if address_highlight is not None and address_highlight.annotation:
        annotation_text = address_highlight.annotation
    elif annotation:
        annotation_text = annotation
    
    # --- BOTTOM TEXT LAYOUT ---
    if address_highlight is not None and annotation_text:
        # ROMANTIC/GIFT MODE: Vertical layout with decreasing boldness
        
        # Prepare annotation text
        max_annotation_length = 100
        if len(annotation_text) > max_annotation_length:
            print(f"⚠ Warning: Annotation text truncated from {len(annotation_text)} to {max_annotation_length} characters.")
            annotation_text = annotation_text[:max_annotation_length - 3] + "..."
        
        annotation_color = THEME.get('annotation_color', THEME['text'])
        
        # Annotation at y=0.145 (light but large - elegant and clean)
        ax.text(0.5, 0.145, annotation_text, transform=ax.transAxes,
                color=annotation_color, ha='center', fontproperties=font_annotation, 
                alpha=0.95, zorder=11)
        
        # Elegant decorative line at y=0.128
        ax.plot([0.38, 0.62], [0.128, 0.128], transform=ax.transAxes, 
                color=THEME['text'], linewidth=0.5, alpha=0.4, zorder=11)
        
        # Date at y=0.108 (clean and readable)
        if date_text:
            ax.text(0.5, 0.108, date_text, transform=ax.transAxes,
                    color=THEME['text'], ha='center', fontproperties=font_date, 
                    alpha=0.80, zorder=11)
        
        # City name at y=0.090 (subtle but visible)
        spaced_city = "  ".join(list(city.upper()))
        ax.text(0.5, 0.090, spaced_city, transform=ax.transAxes,
                color=THEME['text'], ha='center', fontproperties=font_city, 
                alpha=0.65, zorder=11)
        
        # Coordinates at y=0.078 (minimal but present)
        lat, lon = point
        coords = f"{lat:.4f}° N / {lon:.4f}° E" if lat >= 0 else f"{abs(lat):.4f}° S / {lon:.4f}° E"
        if lon < 0:
            coords = coords.replace("E", "W")
        
        ax.text(0.5, 0.078, coords, transform=ax.transAxes,
                color=THEME['text'], alpha=0.50, ha='center', fontproperties=font_coords, zorder=11)
    
    else:
        # NORMAL MODE: City is prominent
        spaced_city = "  ".join(list(city.upper()))
        
        # City name at y=0.14
        ax.text(0.5, 0.14, spaced_city, transform=ax.transAxes,
                color=THEME['text'], ha='center', fontproperties=font_main, zorder=11)
        
        # Decorative line at y=0.125
        ax.plot([0.4, 0.6], [0.125, 0.125], transform=ax.transAxes, 
                color=THEME['text'], linewidth=1, zorder=11)
        
        # Annotation text at y=0.115 (if provided)
        if annotation_text:
            max_annotation_length = 100
            if len(annotation_text) > max_annotation_length:
                print(f"⚠ Warning: Annotation text truncated from {len(annotation_text)} to {max_annotation_length} characters.")
                annotation_text = annotation_text[:max_annotation_length - 3] + "..."
            
            font_annotation = FontProperties(fname=FONTS['light'], size=18) if FONTS else FontProperties(family='monospace', size=18)
            annotation_color = THEME.get('annotation_color', THEME['text'])
            ax.text(0.5, 0.115, annotation_text, transform=ax.transAxes,
                    color=annotation_color, ha='center', fontproperties=font_annotation, 
                    alpha=0.9, zorder=11)
        
        # Country name at y=0.10
        ax.text(0.5, 0.10, country.upper(), transform=ax.transAxes,
                color=THEME['text'], ha='center', fontproperties=font_sub, zorder=11)
        
        # Coordinates at y=0.07
        lat, lon = point
        coords = f"{lat:.4f}° N / {lon:.4f}° E" if lat >= 0 else f"{abs(lat):.4f}° S / {lon:.4f}° E"
        if lon < 0:
            coords = coords.replace("E", "W")
        
        ax.text(0.5, 0.07, coords, transform=ax.transAxes,
                color=THEME['text'], alpha=0.7, ha='center', fontproperties=font_coords, zorder=11)

    # --- ATTRIBUTION (bottom right) ---
    if FONTS:
        font_attr = FontProperties(fname=FONTS['light'], size=8)
    else:
        font_attr = FontProperties(family='monospace', size=8)
    
    ax.text(0.98, 0.02, "© OpenStreetMap contributors", transform=ax.transAxes,
            color=THEME['text'], alpha=0.5, ha='right', va='bottom', 
            fontproperties=font_attr, zorder=11)

    # 5. Save
    print(f"Saving to {output_file}...")
    plt.savefig(output_file, dpi=300, facecolor=THEME['bg'])
    plt.close()
    print(f"✓ Done! Poster saved as {output_file}")

def print_examples():
    """Print usage examples."""
    print("""
City Map Poster Generator
=========================

Usage:
  python create_map_poster.py --city <city> --country <country> [options]

Examples:
  # Iconic grid patterns
  python create_map_poster.py -c "New York" -C "USA" -t noir -d 12000           # Manhattan grid
  python create_map_poster.py -c "Barcelona" -C "Spain" -t warm_beige -d 8000   # Eixample district grid
  
  # Waterfront & canals
  python create_map_poster.py -c "Venice" -C "Italy" -t blueprint -d 4000       # Canal network
  python create_map_poster.py -c "Amsterdam" -C "Netherlands" -t ocean -d 6000  # Concentric canals
  python create_map_poster.py -c "Dubai" -C "UAE" -t midnight_blue -d 15000     # Palm & coastline
  
  # Radial patterns
  python create_map_poster.py -c "Paris" -C "France" -t pastel_dream -d 10000   # Haussmann boulevards
  python create_map_poster.py -c "Moscow" -C "Russia" -t noir -d 12000          # Ring roads
  
  # Organic old cities
  python create_map_poster.py -c "Tokyo" -C "Japan" -t japanese_ink -d 15000    # Dense organic streets
  python create_map_poster.py -c "Marrakech" -C "Morocco" -t terracotta -d 5000 # Medina maze
  python create_map_poster.py -c "Rome" -C "Italy" -t warm_beige -d 8000        # Ancient street layout
  
  # Coastal cities
  python create_map_poster.py -c "San Francisco" -C "USA" -t sunset -d 10000    # Peninsula grid
  python create_map_poster.py -c "Sydney" -C "Australia" -t ocean -d 12000      # Harbor city
  python create_map_poster.py -c "Mumbai" -C "India" -t contrast_zones -d 18000 # Coastal peninsula
  
  # River cities
  python create_map_poster.py -c "London" -C "UK" -t noir -d 15000              # Thames curves
  python create_map_poster.py -c "Budapest" -C "Hungary" -t copper_patina -d 8000  # Danube split
  
  # Address highlighting
  python create_map_poster.py -c "Seattle" -C "USA" -t sunset \\
    --address "300 E Pike St, Seattle, WA 98122" --annotation "Where our story began"
  
  python create_map_poster.py -c "New York" -C "USA" -t noir \\
    --address "350 5th Ave, New York, NY 10118" --marker-style star
  
  python create_map_poster.py -c "Paris" -C "France" -t pastel_dream \\
    --address "Champ de Mars, 5 Avenue Anatole France, 75007 Paris" \\
    --annotation "Our favorite spot" --marker-style pin
  
  # List themes
  python create_map_poster.py --list-themes

Options:
  --city, -c        City name (required)
  --country, -C     Country name (required)
  --theme, -t       Theme name (default: feature_based)
  --distance, -d    Map radius in meters (default: 29000)
  --address         Street address to highlight on the map
  --annotation      Custom text to display below city name
  --marker-style    Marker style: circle, pin, or star (default: circle)
  --list-themes     List all available themes

Distance guide:
  4000-6000m   Small/dense cities (Venice, Amsterdam old center)
  8000-12000m  Medium cities, focused downtown (Paris, Barcelona)
  15000-20000m Large metros, full city view (Tokyo, Mumbai)

Available themes can be found in the 'themes/' directory.
Generated posters are saved to 'posters/' directory.
""")

def list_themes():
    """List all available themes with descriptions."""
    available_themes = get_available_themes()
    if not available_themes:
        print("No themes found in 'themes/' directory.")
        return
    
    print("\nAvailable Themes:")
    print("-" * 60)
    for theme_name in available_themes:
        theme_path = os.path.join(THEMES_DIR, f"{theme_name}.json")
        try:
            with open(theme_path, 'r') as f:
                theme_data = json.load(f)
                display_name = theme_data.get('name', theme_name)
                description = theme_data.get('description', '')
        except:
            display_name = theme_name
            description = ''
        print(f"  {theme_name}")
        print(f"    {display_name}")
        if description:
            print(f"    {description}")
        print()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate beautiful map posters for any city",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python create_map_poster.py --city "New York" --country "USA"
  python create_map_poster.py --city Tokyo --country Japan --theme midnight_blue
  python create_map_poster.py --city Paris --country France --theme noir --distance 15000
  
  # Address highlighting
  python create_map_poster.py --city Seattle --country "USA" --theme sunset \\
    --address "300 E Pike St, Seattle, WA 98122" --annotation "Where our story began"
  
  python create_map_poster.py --city "New York" --country "USA" --theme noir \\
    --address "350 5th Ave, New York, NY 10118" --marker-style star
  
  python create_map_poster.py --city Paris --country France --theme pastel_dream \\
    --address "Champ de Mars, 5 Avenue Anatole France, 75007 Paris" \\
    --annotation "Our favorite spot" --marker-style pin
  
  # List available themes
  python create_map_poster.py --list-themes
        """
    )
    
    parser.add_argument('--city', '-c', type=str, help='City name')
    parser.add_argument('--country', '-C', type=str, help='Country name')
    parser.add_argument('--theme', '-t', type=str, default='feature_based', help='Theme name (default: feature_based)')
    parser.add_argument('--distance', '-d', type=int, default=29000, help='Map radius in meters (default: 29000)')
    parser.add_argument('--address', type=str, help='Street address to highlight on the map (e.g., "300 E Pike St, Seattle, WA 98122")')
    parser.add_argument('--annotation', type=str, help='Custom text to display below city name (e.g., "Where our story began")')
    parser.add_argument('--date', type=str, help='Date text to display (e.g., "June 15, 2019" or "Summer 2020")')
    parser.add_argument('--marker-style', type=str, choices=['circle', 'pin', 'star', 'heart'], default='circle', help='Marker style for highlighted address (default: circle)')
    parser.add_argument('--list-themes', action='store_true', help='List all available themes')
    
    args = parser.parse_args()
    
    # If no arguments provided, show examples
    if len(os.sys.argv) == 1:
        print_examples()
        os.sys.exit(0)
    
    # List themes if requested
    if args.list_themes:
        list_themes()
        os.sys.exit(0)
    
    # Validate required arguments
    if not args.city or not args.country:
        print("Error: --city and --country are required.\n")
        print_examples()
        os.sys.exit(1)
    
    # Validate theme exists
    available_themes = get_available_themes()
    if args.theme not in available_themes:
        print(f"Error: Theme '{args.theme}' not found.")
        print(f"Available themes: {', '.join(available_themes)}")
        os.sys.exit(1)
    
    print("=" * 50)
    print("City Map Poster Generator")
    print("=" * 50)
    
    # Load theme
    THEME = load_theme(args.theme)
    
    # Get coordinates and generate poster
    try:
        coords = get_coordinates(args.city, args.country)
        
        # Initialize address_highlight to None
        address_highlight = None
        
        # Process address if provided (Subtask 9.1)
        if args.address:
            print("\n" + "=" * 50)
            print("Processing address highlight...")
            print("=" * 50)
            
            # Geocode the address
            try:
                address_coords = geocode_address(args.address, args.city, args.country)
            except (GeocodingError, ConnectionError) as e:
                print(f"\n✗ Geocoding failed: {e}")
                os.sys.exit(1)
            
            # Use address coordinates as the map center for better framing
            print(f"✓ Centering map on address location: {address_coords}")
            coords = address_coords
            
            # Get marker colors from theme (Subtask 9.2)
            fill_color, outline_color = get_marker_color(THEME)
            print(f"✓ Marker colors: fill={fill_color}, outline={outline_color}")
            
            # Create AddressHighlight object
            address_highlight = AddressHighlight(
                address=args.address,
                lat=address_coords[0],
                lon=address_coords[1],
                x=0.0,  # Will be calculated during rendering
                y=0.0,  # Will be calculated during rendering
                marker_style=args.marker_style,
                fill_color=fill_color,
                outline_color=outline_color,
                annotation=args.annotation
            )
            print("✓ Address highlight configured")
        
        # Generate output filename with highlighted flag (Subtask 9.3)
        output_file = generate_output_filename(args.city, args.theme, highlighted=(args.address is not None))
        
        # Create poster with address highlight
        create_poster(args.city, args.country, coords, args.distance, output_file, 
                     annotation=args.annotation, address_highlight=address_highlight, date_text=args.date)
        
        print("\n" + "=" * 50)
        print("✓ Poster generation complete!")
        print("=" * 50)
        
    except AddressOutOfBoundsError as e:
        print(f"\n✗ Error: {e}")
        os.sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        os.sys.exit(1)
