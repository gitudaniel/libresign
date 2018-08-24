import React, { Component } from 'react';
import SignaturePad from 'react-signature-pad';
import { Button } from 'react-bootstrap';
import { withRouter } from 'react-router';

import qs from 'querystring';

import './Signature.css';

const AWAIT_SIGNATURE = 0;
const SENDING_SIGNATURE = 1;
const COMPLETED_SIGNATURE = 2;
const AUTH_FAILED = 3;

const SERVICE_URL = 'http://localhost:8000/v1';

class FillField extends Component {
  constructor(props) {
    super(props);

    let searchparams = qs.parse(props.location.search.substr(1));

    console.log(searchparams);

    this.state = Object.assign({
      stage: AWAIT_SIGNATURE,
      docid: searchparams.doc,
      auth: searchparams.auth,
    }, props.location.state);
  }

  clickHandler = async (evt) => {
    let {
      token,
      docid,
    } = this.state;

    evt.preventDefault();

    this.setState({ stage: SENDING_SIGNATURE });

    let url = this.refs.signature.toDataURL();

    let blob = await (await fetch(url)).blob();

    let form = new FormData();
    form.append('fieldId', docid);
    form.append('fieldData', blob);

    let request = new XMLHttpRequest();
    request.open("POST", SERVICE_URL + `/field/${docid}`);
    request.setRequestHeader('Authorization', 'Bearer ' + token);
    request.send(form);

    request.onreadystatechange = () => {
      if (request.readyState === 4 && request.status === 201) {
        this.setState({
          stage: COMPLETED_SIGNATURE,
        })
      }
      else if (request.readyState === 4) {
        this.setState({
          stage: AUTH_FAILED
        })
      }
    };

  }

  render() {
    let {
      stage
    } = this.state;

    if (stage === COMPLETED_SIGNATURE) {
      return <div>The signature has been submitted!</div>;
    }
    if (stage === SENDING_SIGNATURE) {
      return <div>Signing in Progress...</div>;
    }
    if (stage === AUTH_FAILED) {
      return <div>Unable to authenticate, try logging in to sign</div>;
    }

    if (stage !== AWAIT_SIGNATURE) {
      throw new Error("Invalid stage");
    }

    return (
      <div>
        <SignaturePad
          ref="signature"
          clearButton="true"
        />

        <Button
          bsClass="large"
          onClick={this.clickHandler}
        >
          Sign
        </Button>
      </div>
    )
  }
}

export default withRouter(FillField);
