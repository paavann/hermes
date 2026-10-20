export interface NavItem {
  readonly id: string;
  readonly label: string;
  readonly href: string;
}

export interface ProblemStatement {
  readonly id: string;
  readonly text: string;
}

export interface PatternTile {
  readonly id: string;
  readonly left: number;
  readonly top: number;
  readonly width: number;
  readonly height: number;
}

export interface PatternLayout {
  readonly containerHeight: number;
  readonly tiles: readonly PatternTile[];
}

export interface CapabilityCard {
  readonly id: string;
  readonly tag: string;
  readonly prefix: string;
  readonly title: string;
  readonly description: string;
  readonly bgImg?: string;
  readonly telemetry: string;
  readonly action?: string;
}
