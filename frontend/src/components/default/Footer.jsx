import React from 'react';
import footerCharacter from '../../assets/images/footer_character.png';

const Footer = () => {
  return (
    <footer className="footer-fixed">
      <div className="footer-content">
        © 2026 Easy Welfare Guide. All rights reserved.
      </div>
      <img
        src={footerCharacter}
        alt="Footer Character"
        className="footer-character"
      />
    </footer>
  );
};

export default Footer;
