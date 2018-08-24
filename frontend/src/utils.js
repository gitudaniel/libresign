
import { SERVICE_URL } from './config';

export function makeWebRequest(request) {
  return new Promise((resolve, reject) => {
    request.onreadystatechange = () => {
      if (request.readyState === 4) {
        if (request.status >= 200 || request.status < 300) {
          resolve(request);
        }
        else {
          reject(request);
        }
      }
    }
  });
}

export function doLinkAuthentication(accessId) {
  let request = new XMLHttpRequest();

  request.open("POST", SERVICE_URL + '/access');
  request.setRequestHeader('AccessID', accessId);
  request.send();
  
  return makeWebRequest(request)
    .then((request) => {
      if (request.status !== 200)
        throw request;

      return JSON.parse(request.responseText).token;
    });
}

export function queryFieldLocations(token, docId) {
  let request = new XMLHttpRequest();

  request.open("GET", SERVICE_URL + `/document/${docId}/info`);
  request.setRequestHeader('Authorization', `Bearer ${token}`);
  request.send();

  let executor = (request) => {
    return makeWebRequest(request)
      .then((request) => {
        if (request.status !== 200) 
          throw request;

        return JSON.parse(request.responseText);
      })
      .catch((request) => {
        if (request.status !== 503)
          throw request;

        let waitTime = request.getResponseHeader('Retry-After');
        if (!waitTime)
          waitTime = 5;

        return new Promise((resolve) => {
            setTimeout(() => {
              resolve();
            }, waitTime * 1000);
          })
          .then(() => {
            let request = new XMLHttpRequest();
          
            request.open("GET", SERVICE_URL + `/document/${docId}/info`);
            request.setRequestHeader('Authorization', `Bearer ${token}`);
            request.send();

            return executor(request);
          });        
      });
  };

  return executor(request);
}

export function doAgreeTOS(token, docId) {
  let request = new XMLHttpRequest();

  request.open("POST", SERVICE_URL + `/document/${docId}/agree-tos`);
  request.setRequestHeader('Authorization', `Bearer ${token}`);
  request.send();

  let first_time = true;
  let executor = (request) => {
    return makeWebRequest(request)
      .then((request) => {
        if (request.status !== 204)
          throw request;
      })
      .catch((request) => {
        if (request.status !== 401 || !first_time)
          throw request;

        first_time = false;

        request = new XMLHttpRequest();

        request.open("POST", SERVICE_URL + `/document/${docId}/agree-tos`);
        request.setRequestHeader('Authorization', `Bearer ${token}`);
        request.send();

        return executor(request);
      });
  };

  return executor(request);
}
