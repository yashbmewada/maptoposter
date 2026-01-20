# Design Document: Address Highlighting Feature

## Overview

This design extends the City Map Poster Generator to support highlighting specific addresses with visual markers and custom annotation text. The feature integrates seamlessly with the existing rendering pipeline, adding new layers for address markers and annotation text while maintaining the tool's minimalist aesthetic and theme system.

The implementation adds three main components:
1. **Address geocoding and validation** - converts street addresses to map coordinates
2. **Marker rendering** - draws visual indicators at the specified location
3. **Annotation text rendering** - displays custom text in the typography section

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    CLI Parser (argparse)                     │
│  + --address, --annotation, --marker-style parameters        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Address Geocoding Module (NEW)                  │
│  • geocode_address(address, city, country)                   │
│  • validate_coordinates_in_bounds(coords, center, dist)      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  Coordinate Transformer (NEW)                │
│  • transform_latlon_to_map_coords(lat, lon, G)               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Marker Renderer (NEW)                           │
│  • render_address_marker(ax, x, y, style, color)             │
│  • get_marker_color(theme)                                   │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│         Annotation Text Renderer (MODIFIED)                  │
│  • render_typography(ax, city, country, coords, annotation)  │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
User Input (address) 
    → Geocoding Service (Nominatim)
    → Validation (bounds check)
    → Coordinate Transformation (lat/lon → map x/y)
    → Marker Rendering (matplotlib scatter/plot)
    → Annotation Text Rendering (matplotlib text)
    → Final Poster Output
```

## Components and Interfaces

### 1. Address Geocoding Module

**Purpose:** Convert street addresses to geographic coordinates and validate they fall within map bounds.

**Functions:**

```python
def geocode_address(address: str, city: str, country: str) -> Tuple[float, float]:
    """
    Geocode a street address to latitude/longitude coordinates.
    
    Args:
        address: Full street address (e.g., "300 E Pike St, Seattle, WA 98122")
        city: City name for context
        country: Country name for context
    
    Returns:
        Tuple of (latitude, longitude)
    
    Raises:
        ValueError: If address cannot be geocoded
        ConnectionError: If geocoding service is unavailable
    """
    pass

def validate_coordinates_in_bounds(
    address_coords: Tuple[float, float],
    center_coords: Tuple[float, float],
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
    pass

def calculate_distance_between_points(
    point1: Tuple[float, float],
    point2: Tuple[float, float]
) -> float:
    """
    Calculate great circle distance between two lat/lon points in meters.
    Uses Haversine formula.
    
    Args:
        point1: (lat, lon) of first point
        point2: (lat, lon) of second point
    
    Returns:
        Distance in meters
    """
    pass
```

**Implementation Notes:**
- Use existing `Nominatim` geolocator with 1-second rate limiting
- Construct full query string: `f"{address}, {city}, {country}"` for better accuracy
- Cache geocoding results to avoid redundant API calls
- Provide detailed error messages with suggestions for address format

### 2. Coordinate Transformer

**Purpose:** Transform geographic coordinates (lat/lon) to matplotlib axis coordinates (x/y).

**Functions:**

```python
def transform_latlon_to_map_coords(
    lat: float,
    lon: float,
    G: nx.MultiDiGraph
) -> Tuple[float, float]:
    """
    Transform latitude/longitude to map x/y coordinates.
    
    Args:
        lat: Latitude of the address
        lon: Longitude of the address
        G: OSMnx graph with CRS projection information
    
    Returns:
        Tuple of (x, y) in map coordinate system
    """
    pass
```

**Implementation Notes:**
- OSMnx graphs use UTM projection by default
- Use the graph's CRS (Coordinate Reference System) for transformation
- The transformation ensures marker appears at correct location on rendered map
- Handle edge cases where coordinates are at map boundaries

### 3. Marker Renderer

**Purpose:** Draw visual markers at the highlighted address location.

**Functions:**

```python
def get_marker_color(theme: dict) -> Tuple[str, str]:
    """
    Determine marker colors based on theme.
    
    Args:
        theme: Theme dictionary with color definitions
    
    Returns:
        Tuple of (fill_color, outline_color)
    """
    pass

def render_address_marker(
    ax: plt.Axes,
    x: float,
    y: float,
    style: str = 'circle',
    fill_color: str = '#FF0000',
    outline_color: str = '#FFFFFF',
    size: int = 200
) -> None:
    """
    Render a marker at the specified map coordinates.
    
    Args:
        ax: Matplotlib axes object
        x: X coordinate in map space
        y: Y coordinate in map space
        style: Marker style ('circle', 'pin', 'star')
        fill_color: Interior color of marker
        outline_color: Border color of marker
        size: Marker size in points
    """
    pass

def render_circle_marker(ax, x, y, fill_color, outline_color, size):
    """Render a circular marker with outer ring."""
    pass

def render_pin_marker(ax, x, y, fill_color, outline_color, size):
    """Render a map pin style marker."""
    pass

def render_star_marker(ax, x, y, fill_color, outline_color, size):
    """Render a star-shaped marker."""
    pass
```

**Marker Specifications:**

- **Circle Marker:**
  - Outer ring: 1.5x size, outline color, 50% opacity
  - Inner circle: 1.0x size, fill color, 100% opacity
  - Center dot: 0.3x size, outline color, 100% opacity

- **Pin Marker:**
  - Teardrop shape pointing to exact location
  - Rendered using matplotlib Path object
  - Outline and fill with same color scheme

- **Star Marker:**
  - 5-pointed star
  - Uses matplotlib star marker ('*')
  - Layered rendering: large outline + smaller fill

**Rendering Order:**
- z-order = 15 (above gradients at z=10, below text at z=11)

### 4. Theme Integration

**Theme Extensions:**

Add new optional fields to theme JSON files:

```json
{
  "marker_fill": "#FF4444",
  "marker_outline": "#FFFFFF",
  "annotation_color": "#000000"
}
```

**Fallback Logic:**

```python
def get_theme_marker_colors(theme: dict) -> Tuple[str, str]:
    """
    Get marker colors from theme with intelligent fallbacks.
    
    Priority:
    1. Use theme['marker_fill'] and theme['marker_outline'] if defined
    2. Use theme['text'] with high contrast background
    3. Use red (#FF4444) with white outline as last resort
    """
    if 'marker_fill' in theme:
        return theme['marker_fill'], theme.get('marker_outline', '#FFFFFF')
    
    # Calculate luminance of background
    bg_luminance = calculate_luminance(theme['bg'])
    
    if bg_luminance > 0.5:  # Light background
        return '#FF4444', '#FFFFFF'  # Red with white outline
    else:  # Dark background
        return '#FF6666', '#000000'  # Lighter red with black outline
```

### 5. Typography Modifications

**Current Layout:**
```
y=0.14  City name (spaced letters)
y=0.125 Decorative line
y=0.10  Country name
y=0.07  Coordinates
y=0.02  Attribution
```

**New Layout (with annotation):**
```
y=0.14  City name (spaced letters)
y=0.125 Decorative line
y=0.115 Annotation text (NEW)
y=0.10  Country name
y=0.07  Coordinates
y=0.02  Attribution
```

**Modified Function:**

```python
def render_typography(
    ax: plt.Axes,
    city: str,
    country: str,
    coords: Tuple[float, float],
    annotation: Optional[str] = None,
    theme: dict,
    fonts: dict
) -> None:
    """
    Render all text elements on the poster.
    
    Args:
        ax: Matplotlib axes
        city: City name
        country: Country name
        coords: (lat, lon) coordinates
        annotation: Optional custom annotation text
        theme: Theme dictionary
        fonts: Font dictionary
    """
    # Existing city, country, coords rendering...
    
    # NEW: Annotation text
    if annotation:
        font_annotation = FontProperties(fname=fonts['light'], size=18)
        ax.text(0.5, 0.115, annotation, transform=ax.transAxes,
                color=theme.get('annotation_color', theme['text']),
                ha='center', fontproperties=font_annotation, 
                alpha=0.9, zorder=11)
```

## Data Models

### AddressHighlight

```python
@dataclass
class AddressHighlight:
    """Represents a highlighted address on the map."""
    
    address: str                    # Full street address
    lat: float                      # Latitude
    lon: float                      # Longitude
    x: float                        # Map x coordinate
    y: float                        # Map y coordinate
    annotation: Optional[str]       # Custom text
    marker_style: str = 'circle'    # 'circle', 'pin', or 'star'
    
    def is_within_bounds(self, center: Tuple[float, float], radius: float) -> bool:
        """Check if address is within map bounds."""
        pass
```

### MarkerStyle

```python
class MarkerStyle(Enum):
    """Supported marker styles."""
    CIRCLE = 'circle'
    PIN = 'pin'
    STAR = 'star'
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Geocoding Round Trip Consistency

*For any* valid street address that successfully geocodes to coordinates, geocoding the same address multiple times should produce coordinates within 10 meters of each other (accounting for geocoding service variance).

**Validates: Requirements 1.2**

### Property 2: Coordinate Bounds Validation

*For any* address coordinates and map center with radius R, if the great circle distance between them is less than R meters, then `validate_coordinates_in_bounds` should return True.

**Validates: Requirements 1.4**

### Property 3: Coordinate Transformation Preserves Location

*For any* latitude/longitude pair within the map bounds, transforming to map coordinates and then rendering should place the marker within the correct geographic region (verified by checking proximity to nearest road node).

**Validates: Requirements 6.3**

### Property 4: Marker Visibility Contrast

*For any* theme background color, the selected marker color should have a luminance contrast ratio of at least 4.5:1 with the background (WCAG AA standard).

**Validates: Requirements 4.2**

### Property 5: Annotation Text Length Constraint

*For any* annotation text input, if the length exceeds 100 characters, the system should either truncate with ellipsis or reject the input with a clear error message.

**Validates: Requirements 3.5**

### Property 6: Marker Rendering Order

*For any* rendered poster with an address marker, the marker's z-order should be greater than all map layers (roads, water, parks, gradients) and less than text elements.

**Validates: Requirements 2.4**

### Property 7: Distance Calculation Symmetry

*For any* two geographic coordinate pairs (point1, point2), the calculated distance from point1 to point2 should equal the distance from point2 to point1 within floating-point precision tolerance.

**Validates: Requirements 1.4**

### Property 8: Filename Sanitization

*For any* city name and annotation text containing special characters, the generated filename should contain only alphanumeric characters, underscores, and hyphens (filesystem-safe).

**Validates: Requirements 8.4**

### Property 9: Error Message Clarity

*For any* geocoding failure, the error message should contain the attempted address string and at least one actionable suggestion for correction.

**Validates: Requirements 7.1, 7.4**

### Property 10: Theme Color Fallback Chain

*For any* theme dictionary, if marker colors are not explicitly defined, the system should successfully derive contrasting marker colors without throwing exceptions.

**Validates: Requirements 4.2**

## Error Handling

### Geocoding Errors

```python
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
```

### Error Handling Strategy

1. **Geocoding Failures:**
   - Catch `geopy.exc.GeocoderTimedOut` → retry with exponential backoff
   - Catch `geopy.exc.GeocoderServiceError` → inform user service is down
   - No results found → suggest checking address format

2. **Coordinate Validation:**
   - Address outside bounds → calculate required distance and suggest to user
   - Invalid coordinates → validate lat (-90 to 90) and lon (-180 to 180)

3. **Rendering Errors:**
   - Invalid marker style → default to 'circle' with warning
   - Annotation too long → truncate to 100 chars with warning
   - Font loading failure → fallback to system fonts (already implemented)

4. **Rate Limiting:**
   - Implement exponential backoff: 1s, 2s, 4s, 8s
   - Maximum 4 retries before failing
   - Display progress to user during retries

## Testing Strategy

### Unit Tests

**Test Coverage Areas:**

1. **Geocoding Module:**
   - Test successful address geocoding
   - Test geocoding with ambiguous addresses
   - Test geocoding service timeout handling
   - Test invalid address formats
   - Test coordinate bounds validation edge cases

2. **Coordinate Transformation:**
   - Test lat/lon to x/y transformation accuracy
   - Test coordinates at map boundaries
   - Test coordinates at map center
   - Test with different map projections

3. **Marker Rendering:**
   - Test each marker style renders without errors
   - Test marker color selection for light themes
   - Test marker color selection for dark themes
   - Test marker positioning accuracy

4. **Typography:**
   - Test annotation text rendering
   - Test annotation text truncation
   - Test layout with and without annotation
   - Test special characters in annotation

5. **Error Handling:**
   - Test all custom exception types
   - Test error message formatting
   - Test retry logic for rate limiting

### Property-Based Tests

**Configuration:**
- Minimum 100 iterations per property test
- Use `hypothesis` library for Python property-based testing
- Each test tagged with: `# Feature: address-highlighting, Property N: [description]`

**Property Test Implementations:**

1. **Property 1: Geocoding Consistency**
   ```python
   @given(st.text(min_size=10, max_size=100))
   def test_geocoding_consistency(address):
       # Feature: address-highlighting, Property 1: Geocoding round trip consistency
       # Test that geocoding same address produces consistent results
   ```

2. **Property 2: Bounds Validation**
   ```python
   @given(st.floats(-90, 90), st.floats(-180, 180), st.integers(1000, 50000))
   def test_coordinate_bounds_validation(lat, lon, radius):
       # Feature: address-highlighting, Property 2: Coordinate bounds validation
       # Test bounds checking logic
   ```

3. **Property 4: Marker Contrast**
   ```python
   @given(st.text(min_size=7, max_size=7, alphabet='0123456789ABCDEF'))
   def test_marker_visibility_contrast(bg_color):
       # Feature: address-highlighting, Property 4: Marker visibility contrast
       # Test contrast ratio calculation
   ```

4. **Property 7: Distance Symmetry**
   ```python
   @given(st.floats(-90, 90), st.floats(-180, 180), 
          st.floats(-90, 90), st.floats(-180, 180))
   def test_distance_calculation_symmetry(lat1, lon1, lat2, lon2):
       # Feature: address-highlighting, Property 7: Distance calculation symmetry
       # Test Haversine distance is symmetric
   ```

5. **Property 8: Filename Sanitization**
   ```python
   @given(st.text(min_size=1, max_size=50))
   def test_filename_sanitization(text):
       # Feature: address-highlighting, Property 8: Filename sanitization
       # Test all special characters are removed
   ```

### Integration Tests

1. **End-to-End Test:**
   - Generate poster with address "300 E Pike St, Seattle, WA 98122"
   - Verify marker appears on map
   - Verify annotation text is rendered
   - Verify output file is created

2. **Theme Integration Test:**
   - Test with all 17 existing themes
   - Verify marker colors contrast with each theme
   - Verify no rendering errors

3. **CLI Integration Test:**
   - Test all parameter combinations
   - Test with missing required parameters
   - Test with invalid marker styles
   - Test help text display

### Manual Testing Checklist

- [ ] Test with real addresses in different cities
- [ ] Verify marker appears at correct street location
- [ ] Test with addresses outside map bounds
- [ ] Test with very long annotation text
- [ ] Test with special characters in annotation
- [ ] Visual inspection of marker on all themes
- [ ] Test with different marker styles
- [ ] Verify poster aesthetics maintained

## Implementation Notes

### Coordinate System Details

OSMnx graphs use UTM (Universal Transverse Mercator) projection by default. The transformation process:

1. Address geocoded to WGS84 lat/lon (EPSG:4326)
2. Graph uses UTM projection (EPSG:326XX where XX is zone)
3. Transform lat/lon to graph's CRS using `pyproj` or `geopandas`
4. Result is x/y coordinates in meters from UTM zone origin

### Marker Size Scaling

Marker size should scale with map distance:
- Small maps (< 8000m): size = 300 points
- Medium maps (8000-15000m): size = 200 points
- Large maps (> 15000m): size = 150 points

This ensures markers remain visible but not overwhelming.

### Performance Considerations

- Geocoding adds ~1-2 seconds to generation time (network latency)
- Coordinate transformation is negligible (< 10ms)
- Marker rendering adds minimal overhead (< 50ms)
- Overall impact: ~2 seconds additional generation time

### Backward Compatibility

All new parameters are optional. Existing usage patterns continue to work:

```bash
# Existing usage (no changes)
python create_map_poster.py -c "Tokyo" -C "Japan" -t noir

# New usage (opt-in)
python create_map_poster.py -c "Tokyo" -C "Japan" -t noir \
  --address "1-1 Shibuya, Tokyo" --annotation "Our favorite spot"
```

## Future Enhancements

Potential future additions (out of scope for initial implementation):

1. **Multiple Address Markers:** Support highlighting multiple addresses
2. **Custom Marker Icons:** Allow users to upload custom marker images
3. **Address Labels:** Show street name next to marker
4. **Route Drawing:** Draw path between two addresses
5. **Marker Size Control:** `--marker-size` parameter
6. **Marker Opacity:** `--marker-opacity` parameter for subtle highlights
7. **Interactive Preview:** Web interface to preview before generating
