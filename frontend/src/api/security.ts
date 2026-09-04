export interface SecurityStatus {
  status: string;
  lastScan: string;
  openFindings: number;
}

export async function getSecurityStatus(): Promise<SecurityStatus> {
  return { status: 'healthy', lastScan: new Date().toISOString(), openFindings: 0 };
}
