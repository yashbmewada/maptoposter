# Implementation Plan: Address Highlighting Feature

## Overview

This implementation adds address highlighting capabilities to the map poster generator through incremental additions to the existing codebase. The approach focuses on adding new functions while minimizing changes to existing code, ensuring backward compatibility.

## Tasks

- [x] 1. Add command line arguments for address highlighting
  - Add `--address` parameter to accept street address input
  - Add `--annotation` parameter for custom text below city name
  - Add `--marker-style` parameter with choices: circle, pin, star (default: circle)
  - Update help text and examples in argparse configuration
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 2. Implement address geocoding module
  - [x] 2.1 Create `geocode_address()` function
    - Accept address, city, country parameters
    - Use existing Nominatim geolocator with rate limiting
    - Return (latitude, longitude) tuple
    - Raise descriptive errors for geocoding failures
    - _Requirements: 1.1, 1.2, 1.3_

  - [x]* 2.2 Write property test for geocoding consistency
    - **Property 1: Geocoding Round Trip Consistency**
    - **Validates: Requirements 1.2**

  - [x] 2.3 Create `calculate_distance_between_points()` function
    - Implement Haversine formula for great circle distance
    - Accept two (lat, lon) tuples
    - Return distance in meters
    - _Requirements: 1.4_

  - [x]* 2.4 Write property test for distance calculation symmetry
    - **Property 7: Distance Calculation Symmetry**
    - **Validates: Requirements 1.4**

  - [x] 2.5 Create `validate_coordinates_in_bounds()` function
    - Check if address coordinates fall within map radius
    - Use `calculate_distance_between_points()` helper
    - Return boolean result
    - _Requirements: 1.4, 1.5_

  - [x]* 2.6 Write property test for coordinate bounds validation
    - **Property 2: Coordinate Bounds Validation**
    - **Validates: Requirements 1.4**

  - [x]* 2.7 Write unit tests for geocoding error handling
    - Test invalid address formats
    - Test geocoding service timeouts
    - Test out-of-bounds addresses
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [x] 3. Implement coordinate transformation
  - [x] 3.1 Create `transform_latlon_to_map_coords()` function
    - Accept lat, lon, and OSMnx graph G
    - Extract graph's CRS projection
    - Transform WGS84 coordinates to graph's coordinate system
    - Return (x, y) tuple in map space
    - _Requirements: 6.1, 6.2, 6.3_

  - [x]* 3.2 Write property test for coordinate transformation
    - **Property 3: Coordinate Transformation Preserves Location**
    - **Validates: Requirements 6.3**

  - [x]* 3.3 Write unit tests for coordinate transformation edge cases
    - Test coordinates at map center
    - Test coordinates at map boundaries
    - Test with different map projections
    - _Requirements: 6.4_

- [x] 4. Implement marker color selection
  - [x] 4.1 Create `calculate_luminance()` function
    - Accept hex color string
    - Calculate relative luminance using WCAG formula
    - Return luminance value (0.0 to 1.0)
    - _Requirements: 4.2_

  - [x] 4.2 Create `calculate_contrast_ratio()` function
    - Accept two hex color strings
    - Calculate WCAG contrast ratio
    - Return ratio value
    - _Requirements: 4.2_

  - [x] 4.3 Create `get_marker_color()` function
    - Accept theme dictionary
    - Check for theme['marker_fill'] and theme['marker_outline']
    - If not present, calculate contrasting colors based on background
    - Ensure minimum 4.5:1 contrast ratio
    - Return (fill_color, outline_color) tuple
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [x]* 4.4 Write property test for marker visibility contrast
    - **Property 4: Marker Visibility Contrast**
    - **Validates: Requirements 4.2**

  - [x]* 4.5 Write property test for theme color fallback
    - **Property 10: Theme Color Fallback Chain**
    - **Validates: Requirements 4.2**

- [x] 5. Implement marker rendering functions
  - [x] 5.1 Create `render_circle_marker()` function
    - Draw outer ring at 1.5x size with outline color (50% opacity)
    - Draw inner circle at 1.0x size with fill color
    - Draw center dot at 0.3x size with outline color
    - Use z-order=15 for all elements
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 5.2 Create `render_pin_marker()` function
    - Create teardrop-shaped path using matplotlib Path
    - Fill with fill_color and outline with outline_color
    - Point tip to exact coordinates
    - Use z-order=15
    - _Requirements: 2.5_

  - [x] 5.3 Create `render_star_marker()` function
    - Use matplotlib star marker ('*')
    - Layer large outline star with smaller fill star
    - Use z-order=15
    - _Requirements: 2.5_

  - [x] 5.4 Create `render_address_marker()` function
    - Accept ax, x, y, style, fill_color, outline_color, size
    - Dispatch to appropriate marker function based on style
    - Handle invalid marker styles with fallback to circle
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 5.5 Write property test for marker rendering order
    - **Property 6: Marker Rendering Order**
    - **Validates: Requirements 2.4**

  - [ ]* 5.6 Write unit tests for marker rendering
    - Test each marker style renders without errors
    - Test marker positioning accuracy
    - Test with different sizes
    - _Requirements: 2.1, 2.2, 2.3_

- [x] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Modify typography rendering for annotation text
  - [x] 7.1 Update text positioning constants
    - Adjust y-coordinates to accommodate annotation line
    - New layout: city (0.14), line (0.125), annotation (0.115), country (0.10)
    - _Requirements: 3.3_

  - [x] 7.2 Add annotation text rendering
    - Check if annotation parameter is provided
    - Render annotation at y=0.115 with light font, size 18
    - Use theme['annotation_color'] or fallback to theme['text']
    - Center-align with 90% opacity
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [x] 7.3 Add annotation length validation
    - Check annotation length before rendering
    - Truncate to 100 characters with ellipsis if needed
    - Display warning to user if truncated
    - _Requirements: 3.5_

  - [ ]* 7.4 Write property test for annotation text length
    - **Property 5: Annotation Text Length Constraint**
    - **Validates: Requirements 3.5**

  - [ ]* 7.5 Write unit tests for typography modifications
    - Test layout with annotation present
    - Test layout without annotation
    - Test annotation truncation
    - Test special characters in annotation
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 8. Integrate address highlighting into main poster creation
  - [x] 8.1 Modify `create_poster()` function signature
    - Add optional parameters: address_highlight (AddressHighlight object or None)
    - Maintain backward compatibility (default None)
    - _Requirements: 5.3, 5.4_

  - [x] 8.2 Add address highlighting logic to rendering pipeline
    - After road rendering and before gradients
    - Check if address_highlight is provided
    - Call `transform_latlon_to_map_coords()` to get x, y
    - Call `render_address_marker()` with appropriate parameters
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 6.1, 6.2, 6.3_

  - [x] 8.3 Pass annotation to typography rendering
    - Extract annotation from address_highlight object
    - Pass to typography rendering function
    - _Requirements: 3.1, 3.2_

- [x] 9. Update main execution flow
  - [x] 9.1 Add address processing in main block
    - Check if --address argument is provided
    - If yes, call `geocode_address()` with address, city, country
    - Call `validate_coordinates_in_bounds()` with result
    - If out of bounds, raise AddressOutOfBoundsError with suggestion
    - Create AddressHighlight object with results
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [x] 9.2 Add marker color selection
    - Call `get_marker_color()` with loaded theme
    - Store colors in AddressHighlight object
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [x] 9.3 Update filename generation for highlighted posters
    - Modify `generate_output_filename()` to accept optional highlighted flag
    - If address is provided, include "highlighted" in filename
    - Format: `{city}_{theme}_highlighted_{timestamp}.png`
    - _Requirements: 8.1, 8.2, 8.3_

  - [ ]* 9.4 Write property test for filename sanitization
    - **Property 8: Filename Sanitization**
    - **Validates: Requirements 8.4**

- [ ] 10. Add error handling and custom exceptions
  - [ ] 10.1 Create `GeocodingError` exception class
    - Include address and suggestion in error message
    - _Requirements: 7.1, 7.4_

  - [ ] 10.2 Create `AddressOutOfBoundsError` exception class
    - Include address, actual distance, and required distance
    - Suggest increasing --distance parameter
    - _Requirements: 1.5, 7.4_

  - [ ] 10.3 Add retry logic for geocoding rate limits
    - Implement exponential backoff: 1s, 2s, 4s, 8s
    - Maximum 4 retries
    - Display progress to user
    - _Requirements: 7.3_

  - [ ]* 10.4 Write property test for error message clarity
    - **Property 9: Error Message Clarity**
    - **Validates: Requirements 7.1, 7.4**

  - [ ]* 10.5 Write unit tests for error handling
    - Test GeocodingError formatting
    - Test AddressOutOfBoundsError formatting
    - Test retry logic with mocked failures
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

- [ ] 11. Update documentation and help text
  - [ ]* 11.1 Update README.md with address highlighting examples
    - Add new section for address highlighting feature
    - Include example commands with --address and --annotation
    - Add example output showing highlighted poster
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [ ]* 11.2 Update CLI help text
    - Add descriptions for new parameters
    - Include usage examples in epilog
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [ ]* 11.3 Update theme documentation
    - Document new optional theme fields: marker_fill, marker_outline, annotation_color
    - Explain fallback behavior
    - _Requirements: 4.1_

- [ ] 12. Final checkpoint - Integration testing
  - Ensure all tests pass, ask the user if questions arise.

- [x] 13. Create example highlighted poster
  - [x] 13.1 Generate test poster with address "300 E Pike St, Seattle, WA 98122"
    - Use sunset theme
    - Add annotation "Where our story began"
    - Use star marker style
    - Verify marker appears at correct location
    - Verify annotation text is rendered correctly
    - _Requirements: 1.1, 1.2, 2.1, 3.1_

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Focus on core implementation first, comprehensive testing can be added later
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- The implementation maintains backward compatibility - all new parameters are optional
- Existing posters without address highlighting continue to work unchanged
