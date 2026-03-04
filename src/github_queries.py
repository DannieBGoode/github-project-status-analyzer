PROJECT_ID_BY_ORG_QUERY = """
query($owner: String!, $number: Int!) {
  organization(login: $owner) {
    projectV2(number: $number) {
      id
    }
  }
}
"""

PROJECT_ID_BY_USER_QUERY = """
query($owner: String!, $number: Int!) {
  user(login: $owner) {
    projectV2(number: $number) {
      id
    }
  }
}
"""

PROJECT_ITEMS_QUERY = """
query($id: ID!, $itemLimit: Int!, $commentLimit: Int!) {
  node(id: $id) {
    ... on ProjectV2 {
      title
      url
      items(first: $itemLimit) {
        nodes {
          updatedAt
          content {
            ... on PullRequest {
              number
              title
              body
              state
              url
              createdAt
              updatedAt
              comments(last: $commentLimit) {
                totalCount
                nodes {
                  bodyText
                  createdAt
                  updatedAt
                  url
                  author {
                    login
                  }
                }
              }
              reviews { totalCount }
            }
            ... on Issue {
              number
              title
              body
              state
              url
              createdAt
              updatedAt
              comments(last: $commentLimit) {
                totalCount
                nodes {
                  bodyText
                  createdAt
                  updatedAt
                  url
                  author {
                    login
                  }
                }
              }
            }
          }
          fieldValueByName(name: "Status") {
            ... on ProjectV2ItemFieldSingleSelectValue { name }
          }
        }
      }
    }
  }
}
"""
