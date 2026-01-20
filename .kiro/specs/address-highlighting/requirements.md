# Requirements Document

## Introduction

This feature enables users to highlight a specific address on city map posters with a visual marker and custom text annotation. This allows for personalized posters that commemorate special locations such as homes, meeting places, or other meaningful addresses - perfect for anniversary gifts, housewarming presents, or personal keepsakes.

## Glossary

- **Map_Poster_Generator**: The existing system that creates minimalist map posters for cities
- **Address_Highlighter**: The new component that geocodes and marks specific addresses on the map
- **Marker**: A visual indicator (circle, pin, or star) placed at the highlighted address location
- **Annotation_Text**: Custom user-provided text displayed below the highlighted address
- **Geocoding_Service**: Service (Nominatim) that converts street addresses to latitude/longitude coordinates
- **Map_Coordinates**: Latitude and longitude values representing a geographic location

## Requirements

### Requirement 1: Address Input and Geocoding

**User Story:** As a user, I want to provide a specific street address, so that I can highlight a meaningful location on my map poster.

#### Acceptance Criteria

1. WHEN a user provides an address via command line, THE Address_Highlighter SHALL accept the full street address as input
2. WHEN an address is provided, THE Address_Highlighter SHALL geocode it to Map_Coordinates using the Geocoding_Service
3. IF the address cannot be geocoded, THEN THE Address_Highlighter SHALL return a descriptive error message and suggest address format improvements
4. WHEN geocoding succeeds, THE Address_Highlighter SHALL validate that the coordinates fall within the map boundary
5. IF the address coordinates are outside the map boundary, THEN THE Address_Highlighter SHALL warn the user and suggest increasing the distance parameter

### Requirement 2: Visual Address Marker

**User Story:** As a user, I want the highlighted address to be clearly visible on the map, so that it stands out as the focal point of the poster.

#### Acceptance Criteria

1. WHEN an address is successfully geocoded, THE Map_Poster_Generator SHALL place a visual Marker at the address coordinates
2. THE Marker SHALL be rendered with a contrasting color from the theme to ensure visibility
3. THE Marker SHALL consist of a filled circle with an outer ring for emphasis
4. THE Marker SHALL be rendered at z-order 15 to appear above all map layers
5. WHERE a marker style is specified, THE Map_Poster_Generator SHALL support circle, pin, or star marker shapes

### Requirement 3: Custom Annotation Text

**User Story:** As a user, I want to add custom text below the highlighted address, so that I can personalize the poster with a meaningful message.

#### Acceptance Criteria

1. WHEN a user provides annotation text via command line, THE Map_Poster_Generator SHALL display the text below the city name
2. THE Annotation_Text SHALL be rendered in the theme's text color with appropriate font styling
3. THE Annotation_Text SHALL be center-aligned and positioned between the city name and country name
4. WHEN no annotation text is provided, THE Map_Poster_Generator SHALL omit the annotation line
5. THE Annotation_Text SHALL support up to 100 characters to maintain poster aesthetics

### Requirement 4: Theme Integration

**User Story:** As a user, I want the address marker to integrate seamlessly with my chosen theme, so that the poster maintains its aesthetic coherence.

#### Acceptance Criteria

1. WHEN a theme is loaded, THE Map_Poster_Generator SHALL include marker color configuration in the theme
2. WHERE a theme does not specify marker colors, THE Map_Poster_Generator SHALL use intelligent contrast detection to select visible marker colors
3. THE Marker SHALL use the theme's accent color if defined, otherwise use a high-contrast color
4. WHEN rendering the marker, THE Map_Poster_Generator SHALL ensure the marker color contrasts with both the background and road colors

### Requirement 5: Command Line Interface

**User Story:** As a user, I want to specify the address and annotation text via command line arguments, so that I can easily generate personalized posters.

#### Acceptance Criteria

1. THE Map_Poster_Generator SHALL accept an optional `--address` parameter for the street address
2. THE Map_Poster_Generator SHALL accept an optional `--annotation` parameter for custom text
3. WHEN `--address` is provided without `--annotation`, THE Map_Poster_Generator SHALL render only the marker
4. WHEN both parameters are provided, THE Map_Poster_Generator SHALL render both marker and annotation
5. THE Map_Poster_Generator SHALL accept an optional `--marker-style` parameter with values: circle, pin, or star

### Requirement 6: Coordinate Transformation

**User Story:** As a developer, I want to accurately transform geographic coordinates to map pixel coordinates, so that markers appear at the correct location.

#### Acceptance Criteria

1. WHEN address coordinates are obtained, THE Address_Highlighter SHALL transform latitude/longitude to the matplotlib axis coordinate system
2. THE Address_Highlighter SHALL use the same projection as the underlying OSMnx graph
3. WHEN the map is rendered, THE Marker SHALL appear precisely at the address location on the street network
4. THE Address_Highlighter SHALL handle coordinate transformations for all supported map projections

### Requirement 7: Error Handling and Validation

**User Story:** As a user, I want clear error messages when something goes wrong, so that I can correct my input and successfully generate the poster.

#### Acceptance Criteria

1. IF the Geocoding_Service is unavailable, THEN THE Address_Highlighter SHALL return a descriptive error message
2. IF the address is ambiguous, THEN THE Address_Highlighter SHALL display the resolved address and ask for confirmation
3. IF rate limiting occurs, THEN THE Address_Highlighter SHALL wait and retry with exponential backoff
4. WHEN validation fails, THE Map_Poster_Generator SHALL display the error without generating a partial poster
5. THE Map_Poster_Generator SHALL validate that annotation text does not contain special characters that break rendering

### Requirement 8: Output Filename Convention

**User Story:** As a user, I want generated posters with address highlights to have descriptive filenames, so that I can easily identify them.

#### Acceptance Criteria

1. WHEN an address is highlighted, THE Map_Poster_Generator SHALL include "highlighted" in the output filename
2. THE output filename SHALL follow the format: `{city}_{theme}_highlighted_{timestamp}.png`
3. WHEN no address is provided, THE Map_Poster_Generator SHALL use the existing filename format
4. THE Map_Poster_Generator SHALL sanitize address text to create filesystem-safe filenames
