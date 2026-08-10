export function multipartBody(fields: Record<string, File | string | undefined>): Pick<RequestInit, 'body'> {
  const body = new FormData()
  Object.entries(fields).forEach(([key, value]) => {
    if (value !== undefined && value !== '') body.append(key, value)
  })
  return { body }
}
