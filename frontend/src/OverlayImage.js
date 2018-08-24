import React from 'react';

import './OverlayImage.css';

const OverlayImage = ({width, height, x, y, src, alt}) => {
  return [
    <div
      key={'inner-div'}
      style={{
        width: width,
        height: height,
        top: y,
        left: x,
      }}
      className='overlay-div'
    />,
    <img
      className='overlay-image'
      style={{
        width: width,
        height: height,
        top: y,
        left: x
      }}
      src={src}
      alt={alt}
      key={'inner-image'}
    />
  ];
}

export default OverlayImage;
